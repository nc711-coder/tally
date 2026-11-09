from fastapi.testclient import TestClient

from tally import app as appmod
from tally.analyst import Analyst
from tally.runner import Result


class Scripted:
    model = "scripted"

    def __init__(self, *answers):
        self.answers = list(answers)

    def json(self, *a, **k):
        return self.answers.pop(0), {}


def client(*answers):
    appmod._analyst = Analyst(llm=Scripted(*answers), db_url="postgresql://x",
                              runner=lambda q, u: Result(["region", "revenue"], [["West", 10.5], ["Southwest", 20.0]]))
    appmod.limits = appmod.Limits()
    return TestClient(appmod.app)


def test_ask_returns_answer_chart_and_sql():
    c = client({"action": "sql", "tables": ["orders"], "sql": "select 1 from fernwood.orders", "message": ""},
               {"answer": "Southwest led with $20.00.", "follow_ups": ["By month?", "By product?"]})
    r = c.post("/api/ask", json={"question": "Revenue by region"}).json()
    assert r["status"] == "answered" and r["answer"] == "Southwest led with $20.00."
    assert r["chart"]["type"] == "bar" and r["sql"] and r["rows"] == [["West", 10.5], ["Southwest", 20.0]]
    assert r["follow_ups"] == ["By month?", "By product?"]


def test_refusal_has_no_rows():
    c = client({"action": "refuse", "tables": [], "sql": "", "message": "I can only read data."})
    r = c.post("/api/ask", json={"question": "drop everything"}).json()
    assert r["status"] == "refused" and r["rows"] == [] and r["chart"] is None


def test_rate_limit(monkeypatch):
    c = client(*[{"action": "clarify", "tables": [], "sql": "", "message": "Which?"}] * 3)
    appmod.limits.per_hour = 2
    codes = [c.post("/api/ask", json={"question": "best?"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_examples_and_health():
    c = client()
    assert c.get("/health").json() == {"status": "ok"}
    assert len(c.get("/api/examples").json()["examples"]) >= 4
