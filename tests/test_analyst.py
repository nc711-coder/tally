"""The pipeline with a scripted model (no API key needed): what runs, what's blocked, what's retried."""
import pytest

from tally.analyst import REFUSAL, Analyst
from tally.runner import QueryError, Result


class Scripted:
    model = "scripted"

    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def json(self, system, user, schema=None, name="", max_tokens=0):
        self.prompts.append(user)
        return self.answers.pop(0), {}


def sql(q):
    return {"action": "sql", "tables": ["orders"], "sql": q, "message": ""}


class FakeDB:
    def __init__(self, fail_first=False):
        self.ran, self.fail_first = [], fail_first

    def __call__(self, query, url):
        self.ran.append(query)
        if self.fail_first and len(self.ran) == 1:
            raise QueryError('column "revenue" does not exist')
        return Result(["n"], [[7]])


def make(*answers, db=None):
    db = db or FakeDB()
    return Analyst(llm=Scripted(*answers), db_url="postgresql://x", runner=db), db


def test_answers_with_a_checked_limited_query():
    a, db = make(sql("select count(*) as n from fernwood.orders"))
    r = a.ask("How many orders?")
    assert r.status == "answered" and r.rows == [[7]] and r.sql.startswith("select count")
    assert db.ran[0].endswith("limit 1001")


def test_unsafe_query_gets_one_rewrite_then_refused():
    a, db = make(sql("delete from fernwood.orders"), sql("drop table fernwood.orders"))
    r = a.ask("Delete everything")
    assert r.status == "refused" and r.message == REFUSAL and db.ran == []
    assert len(r.attempts) == 2 and all(x["problems"] for x in r.attempts)


def test_unsafe_query_rewritten_safely_runs():
    a, db = make(sql("select * from pg_catalog.pg_roles"), sql("select count(*) n from fernwood.customers"))
    r = a.ask("How many customers")
    assert r.status == "answered" and len(db.ran) == 1
    assert "safety check" in a.llm.prompts[1]


def test_database_error_gets_one_fix():
    a, db = make(sql("select revenue from fernwood.orders"), sql("select count(*) n from fernwood.orders"),
                 db=FakeDB(fail_first=True))
    r = a.ask("Revenue?")
    assert r.status == "answered" and len(db.ran) == 2
    assert 'does not exist' in a.llm.prompts[1]


def test_clarify_and_refuse_pass_through():
    a, _ = make({"action": "clarify", "tables": [], "sql": "", "message": "By revenue or by orders?"})
    assert a.ask("Best customers?").message == "By revenue or by orders?"
    a, db = make({"action": "refuse", "tables": [], "sql": "", "message": "I can only read data."})
    r = a.ask("Drop the table")
    assert r.status == "refused" and db.ran == []


def test_follow_up_includes_the_earlier_query():
    a, _ = make(sql("select 1 as n from fernwood.orders limit 1"))
    a.ask("Break that down by region", history=[{"question": "Revenue last quarter", "sql": "select 42"}])
    assert "Its SQL: select 42" in a.llm.prompts[0]


@pytest.mark.parametrize("q", ["", "   ", "x" * 600])
def test_empty_or_huge_questions_never_reach_the_model(q):
    a, db = make()
    assert a.ask(q).status == "clarify" and db.ran == []
