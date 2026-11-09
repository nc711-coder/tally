"""The safety check every query passes before it reaches the database. Code, not the AI, decides.

    sql, problems = check(query)        # problems == [] means it may run; sql has a row limit added

Rules: one statement; a plain SELECT (WITH ... SELECT and UNION are fine); only the fernwood tables; no
functions that reach outside the query (pg_sleep, pg_read_file, dblink, set_config, ...); no SELECT INTO
(it creates a table) and no FOR UPDATE (it locks rows). The read-only database user is a second wall behind
this one: even a query that slipped past here couldn't change anything.
"""
from __future__ import annotations

import logging

import sqlglot
from sqlglot import exp

from .notes import TABLES

logging.getLogger("sqlglot").setLevel(logging.ERROR)     # it warns when it falls back on odd syntax

ALLOWED = set(TABLES)
MAX_ROWS = 1000
BLOCKED_FUNCTION_PREFIXES = ("pg_", "lo_", "dblink", "set_config", "current_setting", "query_to_xml",
                             "txid_", "inet_", "version", "current_version")
WRITES = (exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop, exp.Alter, exp.Command,
          exp.TruncateTable, exp.Grant, exp.Copy, exp.Set, exp.Transaction, exp.Commit, exp.Rollback)


def check(sql: str) -> tuple[str, list[str]]:
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        return "", ["the query is empty"]
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except sqlglot.errors.ParseError as e:
        return sql, [f"the query isn't valid SQL ({str(e).splitlines()[0][:160]})"]
    if len(statements) != 1:
        return sql, ["only one statement is allowed"]
    tree = statements[0]
    problems = []

    def kind(node) -> str:
        return (str(node.this) if isinstance(node, exp.Command) else node.key).split()[0].upper()

    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        problems.append(f"only SELECT queries may run, not {kind(tree)}")
    for node in tree.walk():
        if isinstance(node, WRITES) and node is not tree:
            problems.append(f"{kind(node)} isn't allowed")
        elif isinstance(node, exp.Into):
            problems.append("SELECT INTO isn't allowed (it creates a table)")
        elif isinstance(node, exp.Lock):
            problems.append("FOR UPDATE / FOR SHARE isn't allowed")

    ctes = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name, schema = table.name.lower(), (table.db or "").lower()
        if not name:
            problems.append("a FROM item that isn't a table (e.g. a function) isn't allowed")
        elif not schema and name in ctes:
            continue
        elif schema not in ("", "fernwood") or name not in ALLOWED:
            problems.append(f"the table {table.sql()} isn't one of Fernwood's tables")

    for fn in tree.find_all(exp.Func):
        fname = (fn.sql_name() if not isinstance(fn, exp.Anonymous) else fn.name).lower()
        if fname.startswith(BLOCKED_FUNCTION_PREFIXES):
            problems.append(f"the function {fname}() isn't allowed")

    problems = list(dict.fromkeys(problems))           # once each, in order
    # One row more than the limit, so the caller can tell the result was cut off.
    limited = f"select * from (\n{sql}\n) as answer limit {MAX_ROWS + 1}"
    return limited, problems
