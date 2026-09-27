from datetime import date

import pytest
import pytest_asyncio

from bot.db import init_db
from bot.repositories.guilds import (
    all_channels,
    get_channel,
    leaderboard,
    register_member,
    set_channel,
)
from bot.repositories.users import link_user

GUILD = 100
OTHER_GUILD = 200
TODAY = date(2026, 9, 27)


@pytest_asyncio.fixture
async def conn(tmp_path):
    connection = await init_db(str(tmp_path / "test.db"))
    yield connection
    await connection.close()


async def add_user(conn, discord_id, name, streak, points, last_solved, guild=GUILD):
    await link_user(conn, discord_id, name)
    await conn.execute(
        "UPDATE users SET current_streak = ?, points = ?, last_solved = ? "
        "WHERE discord_id = ?",
        (streak, points, last_solved, discord_id),
    )
    await conn.commit()
    await register_member(conn, guild, discord_id)


# channels
@pytest.mark.asyncio
async def test_set_and_get_channel(conn):
    await set_channel(conn, GUILD, 555)
    assert await get_channel(conn, GUILD) == 555


@pytest.mark.asyncio
async def test_change_channel(conn):
    await set_channel(conn, GUILD, 555)
    await set_channel(conn, GUILD, 777)
    assert await get_channel(conn, GUILD) == 777


@pytest.mark.asyncio
async def test_unknown_guild_has_no_channel(conn):
    assert await get_channel(conn, 999) is None


@pytest.mark.asyncio
async def test_all_channels_skips_guilds_without_setup(conn):
    await set_channel(conn, GUILD, 555)
    await link_user(conn, 1, "fatma")
    await register_member(conn, OTHER_GUILD, 1)  # creates guild row without channel
    assert await all_channels(conn) == [(GUILD, 555)]


# members
@pytest.mark.asyncio
async def test_register_unlinked_user_does_nothing(conn):
    await register_member(conn, GUILD, 42)
    assert await leaderboard(conn, GUILD, TODAY) == []


@pytest.mark.asyncio
async def test_register_twice_is_fine(conn):
    await link_user(conn, 1, "fatma")
    await register_member(conn, GUILD, 1)
    await register_member(conn, GUILD, 1)
    assert len(await leaderboard(conn, GUILD, TODAY)) == 1


# leaderboard
@pytest.mark.asyncio
async def test_leaderboard_orders_by_streak(conn):
    await add_user(conn, 1, "a", streak=3, points=10, last_solved="2026-09-27")
    await add_user(conn, 2, "b", streak=7, points=5, last_solved="2026-09-26")
    rows = await leaderboard(conn, GUILD, TODAY, by="streak")
    assert [r["discord_id"] for r in rows] == [2, 1]


@pytest.mark.asyncio
async def test_leaderboard_orders_by_points(conn):
    await add_user(conn, 1, "a", streak=3, points=10, last_solved="2026-09-27")
    await add_user(conn, 2, "b", streak=7, points=5, last_solved="2026-09-26")
    rows = await leaderboard(conn, GUILD, TODAY, by="points")
    assert [r["discord_id"] for r in rows] == [1, 2]


@pytest.mark.asyncio
async def test_broken_streak_counts_as_zero(conn):
    await add_user(conn, 1, "a", streak=2, points=0, last_solved="2026-09-27")
    await add_user(conn, 2, "b", streak=30, points=0, last_solved="2026-09-20")
    rows = await leaderboard(conn, GUILD, TODAY, by="streak")
    assert [(r["discord_id"], r["streak"]) for r in rows] == [(1, 2), (2, 0)]


@pytest.mark.asyncio
async def test_leaderboard_only_shows_members_of_that_guild(conn):
    await add_user(conn, 1, "a", streak=1, points=1, last_solved="2026-09-27")
    await add_user(
        conn, 2, "b", streak=9, points=9, last_solved="2026-09-27", guild=OTHER_GUILD
    )
    rows = await leaderboard(conn, GUILD, TODAY)
    assert [r["discord_id"] for r in rows] == [1]


@pytest.mark.asyncio
async def test_leaderboard_limit(conn):
    for i in range(1, 13):
        await add_user(
            conn, i, f"user{i}", streak=i, points=i, last_solved="2026-09-27"
        )
    assert len(await leaderboard(conn, GUILD, TODAY, limit=10)) == 10


@pytest.mark.asyncio
async def test_invalid_ranking_raises(conn):
    with pytest.raises(ValueError):
        await leaderboard(conn, GUILD, TODAY, by="nonsense")
