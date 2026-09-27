import pytest
import pytest_asyncio

from bot.db import init_db
from bot.repositories.guilds import set_channel
from bot.repositories.posts import mark_posted, was_posted

GUILD = 100


@pytest_asyncio.fixture
async def conn(tmp_path):
    connection = await init_db(str(tmp_path / "test.db"))
    await set_channel(connection, GUILD, 555)
    yield connection
    await connection.close()


@pytest.mark.asyncio
async def test_not_posted_initially(conn):
    assert not await was_posted(conn, GUILD, "2026-09-27")


@pytest.mark.asyncio
async def test_mark_and_check(conn):
    await mark_posted(conn, GUILD, "2026-09-27")
    assert await was_posted(conn, GUILD, "2026-09-27")
    assert not await was_posted(conn, GUILD, "2026-09-28")


@pytest.mark.asyncio
async def test_mark_twice_is_fine(conn):
    await mark_posted(conn, GUILD, "2026-09-27")
    await mark_posted(conn, GUILD, "2026-09-27")
    assert await was_posted(conn, GUILD, "2026-09-27")


@pytest.mark.asyncio
async def test_posts_are_per_guild(conn):
    await set_channel(conn, 200, 777)
    await mark_posted(conn, GUILD, "2026-09-27")
    assert not await was_posted(conn, 200, "2026-09-27")
