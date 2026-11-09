"""The web API the page talks to.

    uvicorn tally.app:app --reload          then open http://127.0.0.1:8000/docs

    POST /api/ask       {"question": "...", "history": [{"question", "sql"}]}
        -> {"status", "message", "answer", "follow_ups", "sql", "columns", "rows", "truncated", "chart", "seconds"}
    GET  /api/examples  the example questions shown above the box
    GET  /health        {"status": "ok"}

Limits keep a public demo cheap: QUESTIONS_PER_HOUR per visitor (default 30) and DAILY_QUESTIONS for
everyone together (default 500). ALLOWED_ORIGINS lists the page's address(es) for the browser (CORS).
"""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict, deque
from datetime import date

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .analyst import MAX_QUESTION, Analyst
from .answer import write_answer
from .chart import choose
from .llm import load_dotenv

load_dotenv()
log = logging.getLogger("tally")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

EXAMPLES = [
    "Revenue by region last quarter",
    "Monthly revenue in 2026",
    "Top 5 products by revenue this year",
    "Which 3 products dropped the most from Q2 to Q3 2026?",
    "What share of 2026 revenue came from each channel?",
    "How many subscriptions were cancelled each month this year?",
]

app = FastAPI(title="Tally", version="1.0")
origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"])


class Turn(BaseModel):
    question: str = Field(max_length=MAX_QUESTION)
    sql: str = Field(default="", max_length=4000)


class Ask(BaseModel):
    question: str = Field(max_length=2000)
    history: list[Turn] = Field(default_factory=list, max_length=6)


class Limits:
    def __init__(self):
        self.per_hour = int(os.environ.get("QUESTIONS_PER_HOUR") or 30)
        self.per_day = int(os.environ.get("DAILY_QUESTIONS") or 500)
        self.seen: dict[str, deque] = defaultdict(deque)
        self.day, self.today_count = date.today(), 0
        self.lock = threading.Lock()

    def allow(self, visitor: str) -> str | None:
        """None if allowed, else the reason."""
        now = time.time()
        with self.lock:
            if date.today() != self.day:
                self.day, self.today_count = date.today(), 0
            if self.today_count >= self.per_day:
                return "The demo has answered its questions for today. Please try again tomorrow."
            q = self.seen[visitor]
            while q and now - q[0] > 3600:
                q.popleft()
            if len(q) >= self.per_hour:
                return "That's a lot of questions in an hour. Please wait a little and try again."
            q.append(now)
            self.today_count += 1
        return None


limits = Limits()
_analyst: Analyst | None = None


def analyst() -> Analyst:
    global _analyst
    if _analyst is None:
        _analyst = Analyst()
    return _analyst


def pretty(sql: str) -> str:
    """The query laid out over several lines for reading; unchanged if it can't be reformatted."""
    if not sql:
        return sql
    try:
        import sqlglot
        return sqlglot.transpile(sql, read="postgres", write="postgres", pretty=True)[0]
    except Exception:
        return sql


def visitor(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/examples")
def examples():
    return {"examples": EXAMPLES}


@app.post("/api/ask")
def ask(body: Ask, request: Request):
    why = limits.allow(visitor(request))
    if why:
        return JSONResponse({"status": "limited", "message": why}, status_code=429)
    t = time.perf_counter()
    try:
        a = analyst()
        reply = a.ask(body.question, [h.model_dump() for h in body.history])
    except ConnectionError as e:
        log.error("database unreachable: %s", e)
        return JSONResponse({"status": "failed", "message": "The database isn't reachable right now. "
                                                           "Please try again in a minute."}, status_code=503)
    except RuntimeError as e:
        log.error("not configured: %s", e)
        return JSONResponse({"status": "failed", "message": "The demo isn't set up correctly right now."},
                            status_code=500)
    out = {"status": reply.status, "message": reply.message, "answer": "", "follow_ups": [], "sql": pretty(reply.sql),
           "columns": reply.columns, "rows": reply.rows, "truncated": reply.truncated, "chart": None,
           "seconds": {}}
    if reply.status == "answered":
        tw = time.perf_counter()
        out["answer"], out["follow_ups"], info = write_answer(a.llm, body.question, reply.columns, reply.rows)
        out["chart"] = choose(reply.columns, reply.rows)
        reply.seconds["answer"] = round(time.perf_counter() - tw, 2)
        out["checks"] = {"answer_rewrites": info["rewrites"], "answer_fallback": info["fallback"],
                         "queries_blocked": sum(1 for x in reply.attempts if x.get("problems"))}
    out["seconds"] = {**reply.seconds, "total": round(time.perf_counter() - t, 2)}
    log.info("ask status=%s seconds=%s q=%r", reply.status, out["seconds"]["total"], body.question[:120])
    return out
