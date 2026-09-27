import pytest
import pytest_asyncio

from bot.db import init_db
from bot.repositories.users import LeetCodeNameTaken, get_user, link_user


@pytest_asyncio.fixture
async def conn(tmp_path):
    connection = await init_db(str(tmp_path / "test.db"))
    yield connection
    await connection.close()


@pytest.mark.asyncio
async def test_get_unknown_user_returns_none(conn):
    assert await get_user(conn, 123) is None


@pytest.mark.asyncio
async def test_link_new_user(conn):
    await link_user(conn, 1, "sunny")
    user = await get_user(conn, 1)
    assert user["leetcode_name"] == "sunny"
    assert user["current_streak"] == 0


@pytest.mark.asyncio
async def test_relink_updates_name_and_keeps_streak(conn):
    await link_user(conn, 1, "sunny")
    await conn.execute("UPDATE users SET current_streak = 5 WHERE discord_id = 1")
    await conn.commit()

    await link_user(conn, 1, "sunny_new")
    user = await get_user(conn, 1)
    assert user["leetcode_name"] == "sunny_new"
    assert user["current_streak"] == 5


@pytest.mark.asyncio
async def test_same_leetcode_name_for_two_users_is_rejected(conn):
    await link_user(conn, 1, "sunny")
    with pytest.raises(LeetCodeNameTaken):
        await link_user(conn, 2, "sunny")


@pytest.mark.asyncio
async def test_same_user_relinking_same_name_is_fine(conn):
    await link_user(conn, 1, "sunny")
    await link_user(conn, 1, "sunny")
    assert (await get_user(conn, 1))["leetcode_name"] == "sunny"