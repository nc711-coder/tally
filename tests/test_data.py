from collections import defaultdict
from datetime import date

from tally.generate import COLUMNS, END, START, generate
from tally.notes import TABLES, describe


def test_same_rows_every_time():
    assert generate() == generate()


def test_every_table_has_its_columns():
    t = generate()
    for name, cols in COLUMNS.items():
        assert t[name] and all(len(r) == len(cols) for r in t[name]), name
    assert set(TABLES) == set(COLUMNS)
    for name, t_ in TABLES.items():
        assert list(t_["columns"]) == COLUMNS[name], name


def test_orders_are_in_range_and_items_add_up():
    t = generate()
    assert all(START <= o[2] <= END for o in t["orders"])
    ids = {o[0] for o in t["orders"]}
    for it in t["order_items"]:
        assert it[1] in ids
        assert abs(it[5] - round(it[3] * it[4], 2)) < 0.005


def test_the_patterns_worth_finding_are_there():
    t = generate()
    orders = {o[0]: o for o in t["orders"]}
    names = {p[0]: p[1] for p in t["products"]}
    by = defaultdict(float)
    for it in t["order_items"]:
        o = orders[it[1]]
        if o[5] == "completed":
            by[(names[it[2]], o[2].year)] += it[5]
            by[("month", o[2].year, o[2].month)] += it[5]
    assert by[("Ethiopia Yirgacheffe", 2026)] > 1.5 * by[("Ethiopia Yirgacheffe", 2025)]
    assert by[("month", 2025, 12)] > by[("month", 2025, 11)] > by[("month", 2025, 10)]   # holiday spike
    assert by[("month", 2026, 1)] < by[("month", 2025, 12)]


def test_description_spells_out_the_definitions():
    d = describe()
    assert "status = 'completed'" in d and "Today is 2026-11-01" in d and "fernwood.order_items" in d
