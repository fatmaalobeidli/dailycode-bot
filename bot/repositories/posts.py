import aiosqlite


async def was_posted(conn: aiosqlite.Connection, guild_id: int, date: str) -> bool:
    """True if the daily problem for `date` was already posted in this server."""
    cursor = await conn.execute("SELECT 1 FROM daily_posts WHERE guild_id = ? AND date = ?", (guild_id, date))
    return await cursor.fetchone() is not None


async def mark_posted(conn: aiosqlite.Connection, guild_id: int, date: str) -> None:
    """Remember that the daily problem for `date` was posted in this server."""
    await conn.execute("INSERT OR IGNORE INTO daily_posts (guild_id, date) VALUES (?, ?)", (guild_id, date),)
    await conn.commit()
