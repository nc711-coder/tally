# Tally: ask your data in plain English

Ask a business database a question like *"Which products dropped the most from Q2 to Q3?"* and get the
answer in a sentence, a chart, and the exact SQL behind it. The demo runs on **Fernwood Coffee Roasters**,
a fictional company with two years of sales, customers, subscriptions and marketing spend.

**Live demo:** [tally-nu-sable.vercel.app](https://tally-nu-sable.vercel.app) · built by an AI engineer for small businesses that have the data but no analyst.

## What it does

- **Answers in plain English**, leading with the number: "Revenue was $98,395.00 in September 2026."
- **Picks the chart from the result:** a line for trends, bars for comparisons, a big number for a single value.
- **Shows its work:** the SQL it ran, and the data behind the chart.
- **Asks back** when a question has two meanings ("best customers": by revenue or by orders?).
- **Refuses** anything that would change data or reach outside Fernwood's tables.
- **Handles follow-ups** like "break that down by region".

## How it works

```
question → the AI writes one SELECT → safety check (code) → run as a read-only user → answer + chart
                                         │ fails: one rewrite, then refuse      │ database error: one fix
```

The AI only *writes* the query. Code decides whether it runs:

| Layer | What it stops |
| --- | --- |
| **SQL parser** ([`tally/safety.py`](tally/safety.py)) | Anything but a single `SELECT`: no `INSERT`/`UPDATE`/`DELETE`/`DROP`, no `SELECT INTO`, no `FOR UPDATE`, no other schemas or system tables, no `pg_sleep`/`set_config`-style functions |
| **Read-only database user** ([`tally/db.py`](tally/db.py)) | Even a query that got past the parser can't change anything: the user has `SELECT` on Fernwood's tables only, and read-only sessions |
| **Limits** | 5-second query timeout, at most 1,000 rows, per-visitor and daily question caps |
| **Number check** ([`tally/answer.py`](tally/answer.py)) | Every number in the written answer must appear in the result; otherwise one rewrite, then a plain sentence written by code |

The AI's definitions ("revenue excludes refunds and shipping", "last quarter = Q3 2026") live in one place,
[`tally/notes.py`](tally/notes.py), because most wrong answers in text-to-SQL come from a guessed definition.

## How well it works

Measured with a 60-question test set ([`evals/questions.py`](evals/questions.py)): 50 questions with a
hand-written answer key, plus 4 that should be asked back and 6 that must be refused, and 10 held-out questions. An answer counts
as correct when its result table matches the key's, whatever SQL produced it.

| Test | Questions | Result |
| --- | --- | --- |
| Simple lookups | 15 | 15 correct |
| Joins and groups | 20 | 20 correct |
| Trends and comparisons | 15 | 15 correct |
| Should ask back ("who are our best customers?") | 4 | 4 asked back |
| Must refuse ("delete last month's orders", "drop the table") | 6 | 6 refused, **0 unsafe queries run** |
| **Held-out questions** (written after tuning, never used to tune) | 10 | **10 correct** |

The first run scored 43 of 50; each miss was traced to a missing business definition (for example,
"order counts exclude refunds") or one ambiguous test question, and fixed in the table notes or the
question. Because those fixes were made against the same questions, the held-out set is the fairer
estimate for new questions. Median time per question: about 2 seconds (Groq, `openai/gpt-oss-120b`).

## Run it on your computer

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # DATABASE_URL, READER_PASSWORD, GROQ_API_KEY
python -m tally.db              # loads Fernwood's data, creates the read-only user, prints READER_DATABASE_URL
uvicorn tally.app:app --reload  # the API on http://127.0.0.1:8000
```

The page, in a second terminal (needs [Node.js](https://nodejs.org) 20 or newer):

```powershell
cd web
npm install
npm run dev                     # http://localhost:3000
```

Tests: `python -m pytest` (set `TEST_DATABASE_URL` to a throwaway Postgres database to include the database
tests). The test set: `python -m evals.run`.

## Stack

Python · FastAPI · PostgreSQL (Supabase) · sqlglot · Groq (`openai/gpt-oss-120b`) · Next.js · React ·
Recharts · Google Cloud Run · Vercel. Putting it online: [DEPLOY.md](DEPLOY.md).

## Project layout

| Path | What's in it |
| --- | --- |
| `tally/generate.py` | Fernwood's data, generated with a fixed seed so every number is reproducible |
| `tally/db.py`, `sql/schema.sql` | The tables, the loader, and the read-only user |
| `tally/analyst.py` | Question → SQL → safety check → run, with one retry each way |
| `tally/safety.py` | The SQL safety check |
| `tally/answer.py`, `tally/chart.py` | The checked answer sentence and the chart choice |
| `tally/app.py` | The web API |
| `web/` | The Next.js page |
| `evals/` | The 60-question test set, the result comparison and the report writer |
