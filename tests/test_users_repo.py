from datetime import date, datetime, timezone

import pytest
import pytest_asyncio

from bot.db import init_db
from bot.repositories.problems import save_daily_problem
from bot.repositories.users import (
    AlreadySolved,
    LeetCodeNameTaken,
    count_solves,
    get_user,
    link_user,
    record_solve,
    row_to_streak_state,
)
from bot.services.leetcode import DailyProblem
from bot.services.streaks import StreakState

DAY = date(2026, 9, 27)
SOLVED_AT = datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc)
PROBLEM = DailyProblem("2026-09-27", "Two Sum", "two-sum", "Easy", "url", 55.1, ())


@pytest_asyncio.fixture
async def conn(tmp_path):
    connection = await init_db(str(tmp_path / "test.db"))
    yield connection
    await connection.close()


#link_user/get_user

@pytest.mark.asyncio
async def test_get_unknown_user_returns_none(conn):
    assert await get_user(conn, 123) is None


@pytest.mark.asyncio
async def test_link_new_user(conn):
    await link_user(conn, 1, "fatma")
    user = await get_user(conn, 1)
    assert user["leetcode_name"] == "fatma"
    assert user["current_streak"] == 0


@pytest.mark.asyncio
async def test_relink_updates_name_and_keeps_streak(conn):
    await link_user(conn, 1, "fatma")
    await conn.execute("UPDATE users SET current_streak = 5 WHERE discord_id = 1")
    await conn.commit()

    await link_user(conn, 1, "fatma_new")
    user = await get_user(conn, 1)
    assert user["leetcode_name"] == "fatma_new"
    assert user["current_streak"] == 5


@pytest.mark.asyncio
async def test_same_leetcode_name_for_two_users_is_rejected(conn):
    await link_user(conn, 1, "fatma")
    with pytest.raises(LeetCodeNameTaken):
        await link_user(conn, 2, "fatma")


@pytest.mark.asyncio
async def test_same_user_relinking_same_name_is_fine(conn):
    await link_user(conn, 1, "fatma")
    await link_user(conn, 1, "fatma")
    assert (await get_user(conn, 1))["leetcode_name"] == "fatma"


#record_solve

@pytest.mark.asyncio
async def test_row_to_streak_state_new_user(conn):
    await link_user(conn, 1, "fatma")
    state = row_to_streak_state(await get_user(conn, 1))
    assert state == StreakState(current=0, longest=0, last_solved=None)


@pytest.mark.asyncio
async def test_record_solve_updates_streak_and_points(conn):
    await link_user(conn, 1, "fatma")
    await save_daily_problem(conn, PROBLEM)

    await record_solve(conn, 1, DAY, SOLVED_AT, StreakState(1, 1, DAY), points=2)

    user = await get_user(conn, 1)
    assert user["current_streak"] == 1
    assert user["longest_streak"] == 1
    assert user["last_solved"] == "2026-09-27"
    assert user["points"] == 2
    assert row_to_streak_state(user).last_solved == DAY


@pytest.mark.asyncio
async def test_record_solve_twice_same_day_raises_and_keeps_points(conn):
    await link_user(conn, 1, "fatma")
    await save_daily_problem(conn, PROBLEM)
    await record_solve(conn, 1, DAY, SOLVED_AT, StreakState(1, 1, DAY), points=2)

    with pytest.raises(AlreadySolved):
        await record_solve(conn, 1, DAY, SOLVED_AT, StreakState(2, 2, DAY), points=2)

    user = await get_user(conn, 1)
    assert user["points"] == 2
    assert user["current_streak"] == 1


#count_solves

@pytest.mark.asyncio
async def test_count_solves(conn):
    await link_user(conn, 1, "fatma")
    assert await count_solves(conn, 1) == 0

    await save_daily_problem(conn, PROBLEM)
    await record_solve(conn, 1, DAY, SOLVED_AT, StreakState(1, 1, DAY), points=2)
    assert await count_solves(conn, 1) == 1