import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS guilds (
    guild_id        INTEGER PRIMARY KEY,
    channel_id      INTEGER
);

CREATE TABLE IF NOT EXISTS users (
    discord_id      INTEGER PRIMARY KEY,
    leetcode_name   TEXT UNIQUE NOT NULL,
    points          INTEGER NOT NULL DEFAULT 0,
    current_streak  INTEGER NOT NULL DEFAULT 0,
    longest_streak  INTEGER NOT NULL DEFAULT 0,
    last_solved     TEXT
);

CREATE TABLE IF NOT EXISTS daily_problems (
    date            TEXT PRIMARY KEY,
    slug            TEXT NOT NULL,
    title           TEXT NOT NULL,
    difficulty      TEXT NOT NULL,
    url             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS solves (
    discord_id      INTEGER NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
    date            TEXT NOT NULL REFERENCES daily_problems(date),
    solved_at       TEXT NOT NULL,
    PRIMARY KEY (discord_id, date)
);

CREATE TABLE IF NOT EXISTS daily_posts (
    guild_id        INTEGER NOT NULL,
    date            TEXT NOT NULL,

    PRIMARY KEY (guild_id, date),

    FOREIGN KEY (guild_id)
        REFERENCES guilds(guild_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS guild_members (
    guild_id        INTEGER NOT NULL REFERENCES guilds(guild_id) ON DELETE CASCADE,
    discord_id      INTEGER NOT NULL REFERENCES users(discord_id) ON DELETE CASCADE,
    PRIMARY KEY (guild_id, discord_id)
);
"""


async def init_db(path: str) -> aiosqlite.Connection:
    """Open the database, enable foreign keys and create all tables if missing."""
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.executescript(SCHEMA)
    await conn.commit()
    return conn
