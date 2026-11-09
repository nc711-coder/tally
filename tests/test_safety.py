import pytest

from tally.safety import check

SAFE = [
    "select count(*) from fernwood.orders",
    "select count(*) from orders",
    "with m as (select date_trunc('month', order_date) as m from fernwood.orders) select m, count(*) from m group by m",
    "select name from fernwood.products union select name from fernwood.customers",
    "select o.channel, sum(i.line_total) from fernwood.orders o join fernwood.order_items i using (order_id) group by 1",
]
UNSAFE = [
    "delete from fernwood.orders",
    "update fernwood.products set price = 0",
    "insert into fernwood.orders values (1)",
    "drop table fernwood.orders",
    "select 1; drop table fernwood.orders",
    "select * into fernwood.copy from fernwood.orders",
    "select * from fernwood.orders for update",
    "with x as (delete from fernwood.orders returning *) select * from x",
    "select pg_sleep(30)",
    "select * from pg_catalog.pg_roles",
    "select * from information_schema.tables",
    "select * from docsift.documents",
    "select * from public.chat_sessions",
    "select current_setting('is_superuser')",
    "select version()",
    "copy fernwood.orders to stdout",
    "set role postgres",
    "select * from generate_series(1, 100000000)",
    "",
]


@pytest.mark.parametrize("q", SAFE)
def test_safe(q):
    sql, problems = check(q)
    assert problems == [] and sql.endswith("limit 1001")


@pytest.mark.parametrize("q", UNSAFE)
def test_unsafe(q):
    assert check(q)[1]
