import pytest
import pytest_asyncio

from bot.db import init_db
from bot.repositories.problems import get_daily_problem, save_daily_problem
from bot.services.leetcode import DailyProblem

PROBLEM = DailyProblem(
    date="2026-09-27",
    title="Two Sum",
    slug="two-sum",
    difficulty="Easy",
    url="https://leetcode.com/problems/two-sum/",
    ac_rate=55.1,
    tags=("Array",),
)


@pytest_asyncio.fixture
async def conn(tmp_path):
    connection = await init_db(str(tmp_path / "test.db"))
    yield connection
    await connection.close()


@pytest.mark.asyncio
async def test_save_and_get(conn):
    await save_daily_problem(conn, PROBLEM)
    row = await get_daily_problem(conn, "2026-09-27")
    assert row["slug"] == "two-sum"
    assert row["difficulty"] == "Easy"


@pytest.mark.asyncio
async def test_get_missing_returns_none(conn):
    assert await get_daily_problem(conn, "2000-01-01") is None


@pytest.mark.asyncio
async def test_saving_same_date_twice_does_not_crash(conn):
    await save_daily_problem(conn, PROBLEM)
    await save_daily_problem(conn, PROBLEM)
