from datetime import date, datetime

import aiosqlite

from bot.services.streaks import StreakState


class LeetCodeNameTaken(Exception):
    """Raised when another Discord user alreadu linked this LeetCode account."""


class AlreadySolved(Exception):
    """Raised when a user's solve for that day was already recorded."""


async def get_user(conn: aiosqlite.Connection, discord_id: int) -> aiosqlite.Row | None:
    """Return the user's row, or None if they haven't linked an account."""
    cursor = await conn.execute(
        "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
    )
    return await cursor.fetchone()


async def link_user(
    conn: aiosqlite.Connection, discord_id: int, leetcode_name: str
) -> None:
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
            (discord_id, leetcode_name),
        )
        await conn.commit()
    except (
        aiosqlite.IntegrityError
    ) as e:  # diff Discord user already has this LeetCode name
        await conn.rollback()
        raise LeetCodeNameTaken(leetcode_name) from e


def row_to_streak_state(row: aiosqlite.Row) -> StreakState:
    """Convert a users row into a StreakState."""
    last = row["last_solved"]
    return StreakState(
        current=row["current_streak"],
        longest=row["longest_streak"],
        last_solved=date.fromisoformat(last) if last else None,
    )


async def record_solve(
    conn: aiosqlite.Connection,
    discord_id: int,
    day: date,
    solved_at: datetime,
    new_state: StreakState,
    points: int,
) -> None:
    """Store a solve and update streak + points automatically (one transaction)."""
    try:
        await conn.execute(
            "INSERT INTO solves (discord_id, date, solved_at) VALUES (?, ?, ?)",
            (discord_id, day.isoformat(), solved_at.isoformat()),
        )
        await conn.execute(
            """
            UPDATE users
            SET current_streak = ?,
                longest_streak = ?,
                last_solved = ?,
                points = points + ?
            WHERE discord_id = ?
            """,
            (
                new_state.current,
                new_state.longest,
                new_state.last_solved.isoformat() if new_state.last_solved else None,
                points,
                discord_id,
            ),
        )
        await conn.commit()
    except aiosqlite.IntegrityError as e:
        await conn.rollback()
        if "UNIQUE" in str(e):  # PRIMARY KEY (discord_id, date) already exists
            raise AlreadySolved(day.isoformat()) from e
        raise  # any other integrity problem is a real bug, must raise
