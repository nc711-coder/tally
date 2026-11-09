from tally import db


def test_load_counts(admin_url):
    counts = db.load(admin_url)
    with db.connect(admin_url) as conn:
        for name, n in counts.items():
            assert conn.execute(f"select count(*) from fernwood.{name}").fetchone()[0] == n


def test_reader_can_read_but_never_write(loaded):
    assert db.check_reader(loaded) == []


def test_reader_url_for_supabase_pooler():
    url = db.reader_url("postgresql://postgres.abcref:pw@aws-0-us-west-1.pooler.supabase.com:6543/postgres", "p@ss")
    assert url == "postgresql://fernwood_reader.abcref:p%40ss@aws-0-us-west-1.pooler.supabase.com:6543/postgres"


def test_every_answer_key_runs(loaded):
    from evals.questions import HOLDOUT, QUESTIONS
    from tally.runner import run
    keys = [q for q in QUESTIONS if q[3]]
    assert len(QUESTIONS) == 60 and len(keys) == 50 and len(HOLDOUT) == 10
    for qid, _, _, key in keys + HOLDOUT:
        r = run(key, loaded)
        assert r.rows, qid


def test_runner_stops_slow_queries(loaded):
    import pytest
    from tally.runner import QueryError, run
    with pytest.raises(QueryError, match="longer than 1 seconds"):
        run("select count(*) from fernwood.order_items a, fernwood.order_items b", loaded, timeout_s=1)


def test_runner_is_read_only_even_for_the_admin(admin_url):
    import pytest
    from tally.runner import QueryError, run
    with pytest.raises(QueryError):
        run("delete from fernwood.marketing_spend", admin_url)
