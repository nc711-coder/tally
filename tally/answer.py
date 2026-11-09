"""The one-sentence answer, written from the result and checked so it can't invent a number.

    text, follow_ups = write_answer(llm, question, columns, rows)

The model sees the question and the result rows (up to 40) and writes one or two sentences plus two
follow-up questions. Every number in its sentences must be in the result (as written, or rounded the way
people round: $412,287.50 -> $412,288, $412.3K, 412,300), or in the question itself ("top 5", "2026").
If one isn't, it gets one rewrite naming the number; if that fails too, a plain sentence built by code is
used instead. That's the "no invented numbers" rule from the plan.
"""
from __future__ import annotations

import re

from .llm import LLMError

SYSTEM = """You write the answer line for a data analyst tool at Fernwood Coffee Roasters.
You get a question and the exact result of the query that answers it. Reply with a JSON object:
  "answer": one or two short sentences that answer the question directly, leading with the key number.
            Use ONLY numbers that appear in the result; never calculate new ones (no totals, differences or
            percentages the result doesn't contain). Money as $1,234.56 or $1,235; dates as "October 2026".
            If the result has many rows, name the top one or two and say how many rows there are.
            If the result is empty, say that nothing matched.
  "follow_ups": two short follow-up questions a business owner might ask next, answerable from the same
            database (orders, products, customers, subscriptions, marketing spend)."""

SCHEMA = {"type": "object",
          "properties": {"answer": {"type": "string"},
                         "follow_ups": {"type": "array", "items": {"type": "string"}}},
          "required": ["answer", "follow_ups"]}

NUMBER = re.compile(r"(?<![\w.])-?\$?\d[\d,]*(?:\.\d+)?\s?(?:[kKmM](?![a-z]))?%?")
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]


def numbers_in(text: str) -> list[tuple[str, float]]:
    out = []
    for m in NUMBER.finditer(text):
        raw = m.group(0).strip()
        s = raw.replace("$", "").replace(",", "").replace("%", "").strip()
        mult = 1.0
        if s[-1:] in "kK":
            mult, s = 1e3, s[:-1].strip()
        elif s[-1:] in "mM":
            mult, s = 1e6, s[:-1].strip()
        try:
            out.append((raw, float(s) * mult))
        except ValueError:
            continue
    return out


def _result_numbers(columns: list[str], rows: list[list]) -> list[float]:
    vals = []
    for r in rows:
        for v in r:
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                vals.append(float(v))
            elif isinstance(v, str):
                m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", v)
                if m:                                   # a date gives its year, month and day
                    vals += [float(m.group(1)), float(m.group(2)), float(m.group(3))]
                else:
                    vals += [x for _, x in numbers_in(v)]
    vals.append(float(len(rows)))                      # "5 products", "10 months"
    return vals


def _matches(x: float, raw: str, known: list[float]) -> bool:
    decimals = len(raw.split(".")[1].rstrip("%kKmM ")) if "." in raw else 0
    for v in known:
        for cand in (v, v * 100, v / 100):            # 0.109 written as 10.9%
            if abs(cand - x) <= 0.5 * 10 ** -decimals + 1e-9:
                return True                            # same value at the precision written
            if x and abs(cand - x) <= 0.005 * abs(cand) and re.search(r"[kKmM]|0{2,}(?:\D|$)", raw):
                return True                            # deliberately rounded: $412.3K, 412,300
    return False


def invented(text: str, question: str, columns: list[str], rows: list[list]) -> list[str]:
    """The numbers in `text` that aren't in the result or the question."""
    known = _result_numbers(columns, rows) + [x for _, x in numbers_in(question)]
    q = question.lower()
    for i, name in enumerate(MONTHS, start=1):
        if name in q:
            known.append(float(i))
    return [raw for raw, x in numbers_in(text) if not _matches(x, raw, known)]


def fallback(columns: list[str], rows: list[list]) -> str:
    if not rows:
        return "Nothing matched that question."
    if len(rows) == 1 and len(columns) == 1:
        return f"The answer is {fmt(rows[0][0], columns[0])}."
    return f"Here are the results: {len(rows)} row{'s' if len(rows) != 1 else ''}."


def fmt(v, column: str = "") -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if re.search(r"revenue|sales|profit|spend|value|price|fee|cost|amount|total", column, re.I):
            return f"${v:,.2f}"
        return f"{v:,}" if isinstance(v, int) or float(v).is_integer() else f"{v:,.2f}"
    return str(v)


def write_answer(llm, question: str, columns: list[str], rows: list[list]) -> tuple[str, list[str], dict]:
    """(answer text, follow-up questions, info) — info says whether the check passed or code took over."""
    shown = rows[:40]
    table = "\n".join([" | ".join(columns)] + [" | ".join("" if v is None else str(v) for v in r) for r in shown])
    more = f"\n({len(rows)} rows in total; the first 40 are shown)" if len(rows) > 40 else ""
    prompt = f"Question: {question}\n\nResult ({len(rows)} rows):\n{table}{more}"
    info = {"rewrites": 0, "fallback": False}
    try:
        data, _ = llm.json(SYSTEM, prompt, SCHEMA, name="answer", max_tokens=1500)
        text = str(data.get("answer") or "").strip()
        bad = invented(text, question, columns, rows)
        if bad:
            info["rewrites"] = 1
            data, _ = llm.json(SYSTEM, prompt + f"\n\nYour answer used numbers that aren't in the result: "
                                                f"{', '.join(bad)}. Rewrite it using only the result's numbers.",
                               SCHEMA, name="answer", max_tokens=1500)
            text = str(data.get("answer") or "").strip()
            bad = invented(text, question, columns, rows)
        follow = [str(f).strip() for f in data.get("follow_ups") or [] if str(f).strip()][:2]
    except LLMError:
        text, bad, follow = "", ["(model unavailable)"], []
    if bad or not text:
        info["fallback"] = True
        text = fallback(columns, rows)
    return text, follow, info
