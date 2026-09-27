import aiosqlite
import pytest

from bot.db import init_db


@pytest.mark.asyncio
async def test_init_creates_all_tables(tmp_path):
    conn = await init_db(str(tmp_path / "test.db"))
    cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in await cursor.fetchall()}
    await conn.close()
    assert {"guilds", "users", "daily_problems", "solves", "guild_members"} <= tables


@pytest.mark.asyncio
async def test_init_twice_does_not_crash(tmp_path):
    path = str(tmp_path / "test.db")
    conn = await init_db(path)
    await conn.close()
    conn = await init_db(path)
    await conn.close()


@pytest.mark.asyncio
async def test_foreign_keys_are_enforced(tmp_path):
    conn = await init_db(str(tmp_path / "test.db"))
    with pytest.raises(aiosqlite.IntegrityError):
        await conn.execute(
            "INSERT INTO solves (discord_id, date, solved_at) VALUES (1, '2026-09-27', 'x')"
        )
    await conn.close()


@pytest.mark.asyncio
async def test_duplicate_solve_is_rejected(tmp_path):
    conn = await init_db(str(tmp_path / "test.db"))
    await conn.execute(
        "INSERT INTO users (discord_id, leetcode_name) VALUES (1, 'sunny')"
    )
    await conn.execute(
        "INSERT INTO daily_problems VALUES ('2026-09-27', 'two-sum', 'Two Sum', 'Easy', 'url')"
    )
    await conn.execute("INSERT INTO solves VALUES (1, '2026-09-27', 't1')")
    with pytest.raises(aiosqlite.IntegrityError):
        await conn.execute("INSERT INTO solves VALUES (1, '2026-09-27', 't2')")
    await conn.close()
