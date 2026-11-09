"""Run a checked query as the read-only user and return plain Python values.

    result = run(sql, url)       # Result(columns, rows, truncated, seconds)

Every query runs in a read-only transaction with a 5-second limit, on top of the read-only user's own
settings. Decimals become floats and dates become ISO strings, so results go straight to JSON and charts.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from .safety import MAX_ROWS


class QueryError(RuntimeError):
    """The database refused or failed the query; the message is the database's own, for one fix attempt."""


@dataclass
class Result:
    columns: list[str]
    rows: list[list]
    truncated: bool = False
    seconds: float = 0.0
    sql: str = field(default="", repr=False)


def plain(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.date().isoformat() if v.time() == datetime.min.time() else v.isoformat(timespec="minutes")
    if isinstance(v, date):
        return v.isoformat()
    return v


def run(sql: str, url: str, timeout_s: int = 5) -> Result:
    import psycopg
    t = time.perf_counter()
    try:
        with psycopg.connect(url, prepare_threshold=None, connect_timeout=10) as conn:
            with conn.transaction():
                conn.execute("set transaction read only")
                conn.execute(f"set local statement_timeout = '{int(timeout_s)}s'")
                cur = conn.execute(sql)
                columns = [d.name for d in cur.description or []]
                rows = [[plain(v) for v in r] for r in cur.fetchall()]
    except psycopg.errors.QueryCanceled as e:
        raise QueryError(f"the query took longer than {timeout_s} seconds and was stopped") from e
    except psycopg.OperationalError as e:
        raise ConnectionError(f"couldn't reach the database: {str(e).strip().splitlines()[0]}") from e
    except psycopg.Error as e:
        raise QueryError(str(e).strip().splitlines()[0]) from e
    truncated = len(rows) > MAX_ROWS
    return Result(columns, rows[:MAX_ROWS], truncated, round(time.perf_counter() - t, 3), sql)
