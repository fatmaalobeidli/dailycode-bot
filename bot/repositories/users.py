import aiosqlite

class LeetCodeNameTaken(Exception):
    """Raised when another Discord user alreadu linked this LeetCode account."""

async def get_user(conn: aiosqlite.Connection, discord_id: int) -> aiosqlite.Row | None:
    """Return the user's row, or None if they haven't linked an account."""
    cursor = await conn.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
    return await cursor.fetchone()

async def link_user(conn: aiosqlite.Connection, discord_id: int, leetcode_name: str) -> None:
    """Link a Discord user to a LeetCode account, or aupdate an existing link.
    Streaks and points are kept when a user changes their LeetCode name.
    """
    try:
        await conn.execute(
            """
            INSERT INTO users (discord_id, leetcode_name)
            VALUES (?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET leetcode_name = excluded.leetcode_name
            """,
            (discord_id, leetcode_name)
        )
        await conn.commit()
    except aiosqlite.IntegrityError as e: #diff Discord user already has this LeetCode name
        await conn.rollback()
        raise LeetCodeNameTaken(leetcode_name) from e