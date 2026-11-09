"""Does the analyst's result hold the answer key's rows?

    same(gold_columns, gold_rows, columns, rows) -> bool

Matches by values, not names: every column of the key must be found among the result's columns (extra
columns are fine, column order doesn't matter, row order doesn't matter). Counts must match exactly; money and
ratios within 0.5% (or a cent); a percentage may be written as 10.9 or 0.109; a month may be a date
('2026-01-01'), 'YYYY-MM', or a month number when the key covers a single year.
"""
from __future__ import annotations

import itertools
import re
from collections import Counter


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str) and re.fullmatch(r"-?\d+(\.\d+)?", v.strip()):
        return float(v)
    return None


def _date(v):
    if isinstance(v, str):
        m = re.match(r"^(\d{4})-(\d{2})(?:-(\d{2}))?", v)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3) or '01'}"
    return None


def _alternatives(gold_col: list) -> list[tuple[str, list]]:
    """The ways a gold column may legitimately be written: (kind, values)."""
    alts = [("raw", gold_col)]
    nums = [_num(v) for v in gold_col]
    if all(n is not None for n in nums) and any(isinstance(v, float) for v in gold_col):
        alts += [("pct", [n / 100 for n in nums]), ("pct", [n * 100 for n in nums])]
    dates = [_date(v) for v in gold_col]
    if all(dates):
        years = {d[:4] for d in dates}
        alts.append(("date", dates))
        if len(years) == 1:
            alts.append(("month", [int(d[5:7]) for d in dates]))
            if all(d[5:7] in ("01", "04", "07", "10") for d in dates):
                alts.append(("quarter", [(int(d[5:7]) - 1) // 3 + 1 for d in dates]))
    return alts


def _close(a, b) -> bool:
    if a is None or b is None:
        return a is b
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None:
        if isinstance(a, int) and isinstance(b, int):
            return a == b
        if isinstance(a, int) and float(nb).is_integer():
            return a == int(nb)
        return abs(na - nb) <= max(0.011, 0.005 * abs(na))
    da, db = _date(a), _date(b)
    if da and db:
        return da == db
    return str(a).strip().lower() == str(b).strip().lower()


def _key(v):
    n = _num(v)
    if n is not None:
        return (0, round(n, 1), "")
    d = _date(v)
    return (1, 0, d or str(v).strip().lower())


def _rows_match(gold_rows: list[tuple], rows: list[tuple]) -> bool:
    if len(gold_rows) != len(rows):
        return False
    g = sorted(gold_rows, key=lambda r: tuple(_key(v) for v in r))
    p = sorted(rows, key=lambda r: tuple(_key(v) for v in r))
    if all(all(_close(a, b) for a, b in zip(rg, rp)) for rg, rp in zip(g, p)):
        return True
    # sorting can split near-equal numbers differently: fall back to greedy matching
    left = list(rows)
    for rg in gold_rows:
        hit = next((i for i, rp in enumerate(left) if all(_close(a, b) for a, b in zip(rg, rp))), None)
        if hit is None:
            return False
        left.pop(hit)
    return True


def same(gold_columns: list, gold_rows: list[list], columns: list, rows: list[list]) -> bool:
    if len(gold_rows) != len(rows):
        return False
    if not gold_rows:
        return True
    k = len(gold_columns)
    pred_cols = [[r[j] for r in rows] for j in range(len(columns))]
    gold_cols = [[r[i] for r in gold_rows] for i in range(k)]
    # for each gold column: (alternative values, candidate result columns whose values match as a multiset)
    options = []
    for gc in gold_cols:
        opts = []
        for _, alt in _alternatives(gc):
            ga = sorted(alt, key=_key)
            for j, pc in enumerate(pred_cols):
                pa = sorted(pc, key=_key)
                if all(_close(a, b) for a, b in zip(ga, pa)):
                    opts.append((alt, j))
        if not opts:
            return False
        options.append(opts)
    for combo in itertools.product(*options):
        if len({j for _, j in combo}) < k:
            continue                                   # two key columns can't use the same result column
        gold_alt_rows = list(zip(*[alt for alt, _ in combo]))
        pred_proj = [tuple(r[j] for _, j in combo) for r in rows]
        if _rows_match(gold_alt_rows, pred_proj):
            return True
    return False
