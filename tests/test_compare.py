from evals.compare import same


def test_extra_columns_and_order_dont_matter():
    assert same(["region"], [["Southwest"]], ["region", "customers"], [["Southwest", 985]])
    assert same(["c", "n"], [["a", 1], ["b", 2]], ["n", "c"], [[2, "b"], [1, "a"]])


def test_counts_are_exact_money_close():
    assert not same(["count"], [[1374]], ["orders"], [[1381]])
    assert same(["count"], [[1374]], ["orders"], [[1374.0]])
    assert same(["rev"], [[587375.6]], ["revenue"], [[587375.62]])
    assert not same(["rev"], [[587375.6]], ["revenue"], [[597375.6]])


def test_percent_and_month_forms():
    assert same(["pct"], [[10.9]], ["growth"], [[0.1094]])
    assert same(["m", "r"], [["2026-01-01", 5.0], ["2026-02-01", 6.0]], ["month", "r"], [[1, 5.0], [2, 6.0]])
    assert same(["m", "r"], [["2026-01-01", 5.0]], ["month", "r"], [["2026-01", 5.0]])
    assert same(["m", "r"], [["2026-01-01", 5.0]], ["month", "r"], [["2026-01-01T00:00", 5.0]])


def test_rows_must_line_up():
    gold = [["a", 1.5], ["b", 2.5]]
    assert not same(["c", "v"], gold, ["c", "v"], [["a", 2.5], ["b", 1.5]])
    assert not same(["c"], [["a"], ["b"]], ["c"], [["a"]])
