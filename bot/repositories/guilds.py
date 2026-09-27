from datetime import date, timedelta

import aiosqlite


async def set_channel(
    conn: aiosqlite.Connection, guild_id: int, channel_id: int
) -> None:
    """Set (or change) the channel where the daily problem gets posted."""
    await conn.execute(
        """
        INSERT INTO guilds (guild_id, channel_id) VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id
        """,
        (guild_id, channel_id),
    )
    await conn.commit()


async def get_channel(conn: aiosqlite.Connection, guild_id: int) -> int | None:
    """Return the configured channel id for a server, or None."""
    cursor = await conn.execute(
        "SELECT channel_id FROM guilds WHERE guild_id = ?", (guild_id,)
    )
    row = await cursor.fetchone()
    return row["channel_id"] if row else None


async def all_channels(conn: aiosqlite.Connection) -> list[tuple[int, int]]:
    """All (guild_id, channel_id) pairs with a configured channel."""
    cursor = await conn.execute(
        "SELECT guild_id, channel_id FROM guilds WHERE channel_id IS NOT NULL"
    )
    return [(row["guild_id"], row["channel_id"]) for row in await cursor.fetchall()]


async def register_member(
    conn: aiosqlite.Connection, guild_id: int, discord_id: int
) -> None:
    """
    Remember that a linked user belongs to a server (for per-server leaderboards).
    Does nothing if the user hasn't linked a LeetCode account.
    """
    cursor = await conn.execute(
        "SELECT 1 FROM users WHERE discord_id = ?", (discord_id,)
    )
    if await cursor.fetchone() is None:
        return
    await conn.execute(
        "INSERT OR IGNORE INTO guilds (guild_id) VALUES (?)", (guild_id,)
    )
    await conn.execute(
        "INSERT OR IGNORE INTO guild_members (guild_id, discord_id) VALUES (?, ?)",
        (guild_id, discord_id),
    )
    await conn.commit()


async def leaderboard(
    conn: aiosqlite.Connection,
    guild_id: int,
    today: date,
    by: str = "streak",
    limit: int = 10,
) -> list[aiosqlite.Row]:
    """
    Top users of a server, ranked by live streak or by points.
    A streak only counts if the last solve was today or yesterday; otherwise it's 0.
    """
    if by not in ("streak", "points"):
        raise ValueError(f"Unknown ranking: {by}")

    yesterday = (today - timedelta(days=1)).isoformat()
    order = (
        "streak DESC, u.points DESC" if by == "streak" else "u.points DESC, streak DESC"
    )
    cursor = await conn.execute(
        f"""
        SELECT u.discord_id,
               u.leetcode_name,
               u.points,
               u.longest_streak,
               CASE WHEN u.last_solved >= ? THEN u.current_streak ELSE 0 END AS streak
        FROM guild_members gm
        JOIN users u ON u.discord_id = gm.discord_id
        WHERE gm.guild_id = ?
        ORDER BY {order}, u.discord_id
        LIMIT ?
        """,
        (yesterday, guild_id, limit),
    )
    return await cursor.fetchall()
