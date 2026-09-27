import aiosqlite

from bot.services.leetcode import DailyProblem


async def save_daily_problem(conn: aiosqlite.Connection, problem: DailyProblem) -> None:
    """Store the daily problem. Does nothing if that date is already stored."""
    await conn.execute(
        """
        INSERT OR IGNORE INTO daily_problems (date, slug, title, difficulty, url)
        VALUES (?, ?, ?, ?, ?)
        """,
        (problem.date, problem.slug, problem.title, problem.difficulty, problem.url),
    )
    await conn.commit()


async def get_daily_problem(
    conn: aiosqlite.Connection, date: str
) -> aiosqlite.Row | None:
    """Return the stored daily problem for `date` ('YYYY-MM-DD'), or None."""
    cursor = await conn.execute("SELECT * FROM daily_problems WHERE date = ?", (date,))
    return await cursor.fetchone()
