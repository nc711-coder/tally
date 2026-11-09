"""Load the Fernwood demo data and set up the read-only user Tally queries with.

    python -m tally.db            create the fernwood schema, load the data, create/refresh the read-only user
    python -m tally.db --check    only check the read-only user (it can read, and can't change anything)

.env:
    DATABASE_URL=postgresql://postgres...      your admin connection (the same Supabase project is fine)
    READER_PASSWORD=...                        a password you make up for the read-only user
    READER_DATABASE_URL=postgresql://fernwood_reader...    printed by this script; what the app uses

The read-only user ("fernwood_reader") can only SELECT from the fernwood tables. Its sessions are read-only
and stop any query after 5 seconds, so even a bad query can't change data or tie up the database.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from .generate import COLUMNS, generate
from .llm import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "fernwood"
READER = "fernwood_reader"
TABLES = list(COLUMNS)


def connect(url: str, **kw):
    import psycopg
    return psycopg.connect(url, autocommit=True, prepare_threshold=None, **kw)   # None: Supabase's pooler


def load(url: str) -> dict[str, int]:
    """Recreate the schema and load every table. Returns the row counts."""
    tables = generate()
    with connect(url) as conn:
        conn.execute((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        with conn.transaction():
            for name in TABLES:                       # in this order, so foreign keys are satisfied
                cols = ", ".join(COLUMNS[name])
                with conn.cursor() as cur, cur.copy(f"copy {SCHEMA}.{name} ({cols}) from stdin") as copy:
                    for row in tables[name]:
                        copy.write_row(row)
            conn.execute(f"analyze {SCHEMA}.orders; analyze {SCHEMA}.order_items")
    return {k: len(v) for k, v in tables.items()}


def create_reader(url: str, password: str) -> None:
    """The read-only login role: SELECT on the fernwood tables and nothing else."""
    from psycopg import sql
    with connect(url) as conn:
        exists = conn.execute("select 1 from pg_roles where rolname = %s", (READER,)).fetchone()
        if exists:
            # Only the password is updated: on Supabase the admin isn't a superuser, and an ALTER that names
            # role attributes (NOSUPERUSER, ...) is refused. The attributes were set when the role was created.
            conn.execute(sql.SQL("alter role {} login password {}")
                         .format(sql.Identifier(READER), sql.Literal(password)))
        else:
            conn.execute(sql.SQL("create role {} login password {} nosuperuser nocreatedb nocreaterole noinherit")
                         .format(sql.Identifier(READER), sql.Literal(password)))
        for stmt in [
            f"revoke all on schema {SCHEMA} from public",
            f"grant usage on schema {SCHEMA} to {READER}",
            f"grant select on all tables in schema {SCHEMA} to {READER}",
            f"alter role {READER} set default_transaction_read_only = on",
            f"alter role {READER} set statement_timeout = '5s'",
            f"alter role {READER} set search_path = {SCHEMA}",
        ]:
            conn.execute(stmt)


def reader_url(admin_url: str, password: str) -> str:
    """The admin URL with the reader's name and password. Supabase's pooler wants "<role>.<project ref>"."""
    parts = urlsplit(admin_url)
    user = parts.username or ""
    name = f"{READER}.{user.split('.', 1)[1]}" if "." in user else READER
    host = parts.hostname + (f":{parts.port}" if parts.port else "")
    return urlunsplit((parts.scheme, f"{name}:{quote(password, safe='')}@{host}", parts.path, parts.query, ""))


def check_reader(url: str) -> list[str]:
    """Problems with the read-only user (empty = all good): it must read, and must not be able to write."""
    import psycopg
    problems = []
    with connect(url) as conn:
        n = conn.execute(f"select count(*) from {SCHEMA}.orders").fetchone()[0]
        if not n:
            problems.append("it can't see any orders (was the data loaded?)")
        for attempt in [f"delete from {SCHEMA}.orders where order_id = 1",
                        f"update {SCHEMA}.products set price = 0",
                        f"insert into {SCHEMA}.marketing_spend values ('2030-01-01', 'x', 1)",
                        f"create table {SCHEMA}.oops (x int)",
                        f"drop table {SCHEMA}.orders"]:
            try:
                conn.execute(attempt)
                problems.append(f"it was allowed to run: {attempt}")
            except psycopg.Error:
                pass
        timeout = conn.execute("show statement_timeout").fetchone()[0]
        if timeout != "5s":
            problems.append(f"its query time limit is {timeout}, not 5s")
    return problems


def main(argv: list[str]) -> int:
    load_dotenv()
    admin = os.environ.get("DATABASE_URL")
    password = os.environ.get("READER_PASSWORD")
    if not admin or not password:
        print("Set DATABASE_URL and READER_PASSWORD in .env first (see .env.example).")
        return 2
    if "--check" not in argv:
        print("Loading Fernwood's data...")
        for name, n in load(admin).items():
            print(f"  {name:16} {n:>7,} rows")
        create_reader(admin, password)
        print(f"Read-only user '{READER}' is ready.")
    url = os.environ.get("READER_DATABASE_URL") or reader_url(admin, password)
    problems = check_reader(url)
    if problems:
        print("The read-only user has problems:\n  - " + "\n  - ".join(problems))
        return 1
    print("Checked: the read-only user can read the data and can't change anything.")
    if not os.environ.get("READER_DATABASE_URL"):
        print("\nAdd this line to .env (it contains the reader's password, so keep it out of chat):")
        print(f"READER_DATABASE_URL={url}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
