import os

import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def admin_url():
    if not TEST_DB:
        pytest.skip("set TEST_DATABASE_URL to a throwaway Postgres database to run the database tests")
    return TEST_DB


@pytest.fixture(scope="session")
def loaded(admin_url):
    from tally import db
    db.load(admin_url)
    db.create_reader(admin_url, "test-reader-pw")
    return db.reader_url(admin_url, "test-reader-pw")
