from tally.answer import invented, numbers_in, write_answer
from tally.chart import choose
from tally.llm import LLMError


def test_numbers_in_text():
    got = [x for _, x in numbers_in("Revenue was $412,287.50 in Q3, up 8% to 412.3K across 5 regions")]
    assert got == [412287.5, 8.0, 412300.0, 5.0]          # "Q3" is a label, not a number


def test_invented_numbers_are_caught():
    cols, rows = ["region", "revenue"], [["Southwest", 61296.5], ["West", 49766.5]]
    q = "Revenue by region last quarter"
    assert invented("Southwest led with $61,296.50, ahead of the West at $49,766.50.", q, cols, rows) == []
    assert invented("Southwest led with $61,297 (about $61.3K).", q, cols, rows) == []
    assert invented("Southwest led with $61,296.50, 23% more than the West.", q, cols, rows) == ["23%"]
    assert invented("Total revenue was $111,063.", q, cols, rows) == ["$111,063"]


def test_dates_counts_and_question_numbers_are_allowed():
    cols, rows = ["month", "revenue"], [["2026-10-01", 109396.6]] + [["2026-09-01", 98395.0]]
    assert invented("October 2026 was the best of the 2 months at $109,396.60.", "top 2 months", cols, rows) == []
    assert invented("Growth was 10.9%.", "growth?", ["growth_pct"], [[0.109]]) == []


class Scripted:
    def __init__(self, *answers):
        self.answers = list(answers)

    def json(self, *a, **k):
        x = self.answers.pop(0)
        if isinstance(x, Exception):
            raise x
        return x, {}


def test_rewrite_then_fallback():
    cols, rows = ["orders"], [[1374]]
    ok, _, info = write_answer(Scripted({"answer": "1,374 orders.", "follow_ups": ["a", "b"]}), "q", cols, rows)
    assert ok == "1,374 orders." and info == {"rewrites": 0, "fallback": False}
    text, _, info = write_answer(Scripted({"answer": "1,400 orders.", "follow_ups": []},
                                          {"answer": "About 1,374 orders.", "follow_ups": []}), "q", cols, rows)
    assert text == "About 1,374 orders." and info["rewrites"] == 1
    text, _, info = write_answer(Scripted({"answer": "99 orders", "follow_ups": []},
                                          {"answer": "98 orders", "follow_ups": []}), "q", cols, rows)
    assert info["fallback"] and text == "The answer is 1,374."
    text, _, info = write_answer(Scripted(LLMError("down")), "q", cols, rows)
    assert info["fallback"]


def test_chart_choice():
    assert choose(["revenue"], [[5.0]])["type"] == "number"
    line = choose(["month", "revenue"], [["2026-01-01", 1.0], ["2026-02-01", 2.0]])
    assert line["type"] == "line" and line["x"] == "month" and line["formats"]["revenue"] == "money"
    bar = choose(["region", "revenue"], [["West", 1.0], ["Southwest", 2.0]])
    assert bar["type"] == "bar" and not bar["horizontal"]
    assert choose(["name", "units"], [[f"Product number {i}", i] for i in range(8)])["horizontal"]
    assert choose(["name"], [["a"], ["b"]])["type"] == "table"
    assert choose(["channel", "share_pct"], [["web", 24.7], ["wholesale", 59.4]])["formats"]["share_pct"] == "percent"


def test_fallback_still_states_the_key_fact():
    from tally.answer import fallback, invented
    cols, rows = ["region", "revenue"], [["West", 49766.5], ["Southwest", 71569.65]]
    text = fallback(cols, rows)
    assert text == "Southwest has the highest revenue, at $71,569.65, of 2 shown."
    assert invented(text, "Revenue by region", cols, rows) == []
    cols, rows = ["month", "revenue"], [["2026-09-01", 98395.0], ["2026-10-01", 109396.6]]
    text = fallback(cols, rows)
    assert text == "Revenue was $109,396.60 in October 2026, the latest of 2 periods shown."
    assert invented(text, "Monthly revenue", cols, rows) == []
