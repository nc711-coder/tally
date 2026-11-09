"""Pick a chart from the shape of the result. Code decides, so the same result always gets the same chart.

    spec = choose(columns, rows)
    {"type": "number" | "line" | "bar" | "table", "x": "month", "y": ["revenue"], "formats": {"revenue": "money"}}

- one value                       -> a big number
- dates down the first column     -> a line (up to 3 measures)
- names + numbers, 2 to 25 rows   -> bars, sideways when the names are long or there are more than 6
- anything else                   -> a table
"""
from __future__ import annotations

import re

MONEY = re.compile(r"revenue|sales|profit|spend|value|price|fee|cost|amount|total|aov", re.I)
PERCENT = re.compile(r"pct|percent|share|rate|growth|ratio_pct", re.I)
DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?")


def column_format(name: str, values: list) -> str:
    if not values or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values if v is not None):
        return "text"
    if PERCENT.search(name):
        return "percent"
    if MONEY.search(name):
        return "money"
    return "number"


def choose(columns: list[str], rows: list[list]) -> dict:
    cols = [[r[i] for r in rows] for i in range(len(columns))]
    formats = {c: column_format(c, v) for c, v in zip(columns, cols)}
    numeric = [c for c in columns if formats[c] in ("money", "percent", "number")]
    spec = {"type": "table", "x": None, "y": [], "formats": formats, "horizontal": False}
    if not rows:
        return spec
    if len(rows) == 1 and len(columns) == 1 and numeric:
        return {**spec, "type": "number", "y": numeric}
    first = columns[0]
    first_vals = cols[0]
    measures = [c for c in numeric if c != first and not c.endswith("_id")]
    if not measures:
        return spec
    if len(rows) >= 2 and all(isinstance(v, str) and DATE.match(v) for v in first_vals):
        units = {formats[c] for c in measures[:3]}
        y = measures[:3] if len(units) == 1 else measures[:1]       # one axis: same kind of number only
        return {**spec, "type": "line", "x": first, "y": y}
    if 2 <= len(rows) <= 25 and formats[first] == "text":
        longest = max(len(str(v)) for v in first_vals)
        units = {formats[c] for c in measures[:2]}
        y = measures[:2] if len(units) == 1 else measures[:1]
        return {**spec, "type": "bar", "x": first, "y": y, "horizontal": len(rows) > 6 or longest > 12}
    return spec
