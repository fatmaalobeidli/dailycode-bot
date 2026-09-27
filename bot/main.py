import asyncio
import os
from datetime import date, datetime, time, timezone

import aiohttp
import aiosqlite
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

from bot.db import init_db
from bot.repositories import guilds, posts, users
from bot.repositories.problems import save_daily_problem
from bot.services import streaks
from bot.services.leetcode import (
    DailyProblem,
    LeetCodeError,
    fetch_daily,
    fetch_recent_accepted,
    user_exists,
)
from bot.services.solves import find_solve_on, points_for

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")
DB_PATH = os.getenv("DB_PATH", "dailycode.db")

if TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN missing. Did you create the .env file?")


class DailyCodeBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)  # slash commands registry
        self.http_session: aiohttp.ClientSession | None = None
        self.db: aiosqlite.Connection | None = None

    async def setup_hook(self):  # send command list to Discord
        """Runs once before the bot connects."""
        self.http_session = aiohttp.ClientSession()
        self.db = await init_db(DB_PATH)
        daily_post_loop.start()  # NEW: start the automatic daily post

        if DEV_GUILD_ID:
            guild = discord.Object(id=int(DEV_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Commands synced to development guild {DEV_GUILD_ID}")
        else:
            await self.tree.sync()
            print("Global commands synced")

    async def close(self):
        """Runs on shutdown: close HTTP session and database."""
        daily_post_loop.cancel()  # NEW
        if self.http_session:
            await self.http_session.close()
        if self.db:
            await self.db.close()
        await super().close()

    async def on_ready(self):
        print(f"Logged in as {self.user} | ID: {self.user.id}")


bot = DailyCodeBot()


async def remember_member(interaction: discord.Interaction) -> None:
    """Record that the user belongs to this server (for /leaderboard)."""
    if interaction.guild is not None:
        await guilds.register_member(bot.db, interaction.guild.id, interaction.user.id)


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    command = interaction.command.name if interaction.command else "?"
    print(f"[error] /{command}: {error!r}")
    message = "Something went wrong. Please try again later."
    if interaction.response.is_done():
        await interaction.followup.send(
            message, ephemeral=True
        )  # only user who ran cmd sees the msg
    else:
        await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name="ping", description="Check if the bot is alive")  # /ping
async def ping(interaction: discord.Interaction):
    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! {latency_ms} ms")


DIFFICULTY_COLORS = {
    "Easy": discord.Color.green(),
    "Medium": discord.Color.orange(),
    "Hard": discord.Color.red(),
}


# NEW: shared by /daily, /postnow and the automatic post
def build_daily_embed(problem: DailyProblem, description: str | None = None) -> discord.Embed:
    embed = discord.Embed(
        title=problem.title,
        url=problem.url,
        description=description,
        color=DIFFICULTY_COLORS.get(problem.difficulty, discord.Color.blurple()),
    )
    embed.add_field(name="Difficulty", value=problem.difficulty)
    embed.add_field(name="Acceptance", value=f"{problem.ac_rate}%")
    if problem.tags:
        embed.add_field(name="Topics", value=", ".join(problem.tags), inline=False)
    embed.set_footer(text=f"Daily problem: {problem.date}")
    return embed


@bot.tree.command(name="daily", description="Show today's LeetCode problem")
async def daily(interaction: discord.Interaction):
    await interaction.response.defer()  # 15 mins to send the answer instead of 3 s

    try:
        problem = await fetch_daily(bot.http_session)
    except LeetCodeError as e:
        print(f"[daily] {e}")
        await interaction.followup.send(
            "Couldn't reach LeetCode right now. Try again later."
        )
        return

    await interaction.followup.send(embed=build_daily_embed(problem))  # CHANGED


@bot.tree.command(name="link", description="Link your LeetCode account")
@app_commands.describe(username="Your LeetCode username")
async def link(interaction: discord.Interaction, username: str):
    await interaction.response.defer(ephemeral=True)
    username = username.strip()

    try:
        exists = await user_exists(bot.http_session, username)
    except LeetCodeError as e:
        print(f"[link] {e}")
        await interaction.followup.send(
            "Couldn't reach LeetCode right now. Try again later."
        )
        return

    if not exists:
        await interaction.followup.send(
            f"LeetCode user **{username}** doesn't exist. Check the spelling."
        )
        return

    try:
        await users.link_user(bot.db, interaction.user.id, username)
    except users.LeetCodeNameTaken:
        await interaction.followup.send(
            f"**{username}** is already linked to another Discord account."
        )
        return

    await remember_member(interaction)
    await interaction.followup.send(f"Linked to LeetCode account **{username}**.")


@bot.tree.command(name="solved", description="Check if you solved today's problem")
async def solved(interaction: discord.Interaction):
    await interaction.response.defer()  # public: others in the server see your solve

    # Is the user linked?
    user = await users.get_user(bot.db, interaction.user.id)
    if user is None:
        await interaction.followup.send(
            "You haven't linked a LeetCode account yet. Use `/link` first."
        )
        return
    await remember_member(interaction)

    # Today's problem and the user's recent accepted submissions
    try:
        problem = await fetch_daily(bot.http_session)
        await save_daily_problem(bot.db, problem)
        submissions = await fetch_recent_accepted(
            bot.http_session, user["leetcode_name"]
        )
    except LeetCodeError as e:
        print(f"[solved] {e}")
        await interaction.followup.send(
            "Couldn't reach LeetCode right now. Try again later."
        )
        return

    # Was today's problem solved today? LeetCode's date is the reference
    today = date.fromisoformat(problem.date)
    submission = find_solve_on(submissions, problem.slug, today)
    if submission is None:
        await interaction.followup.send(
            f"No accepted submission for **{problem.title}** found today. "
            "Solve it and try again! (Your submissions must be public.)"
        )
        return

    # Save solve + update streak and points in one transaction
    old_state = users.row_to_streak_state(user)
    new_state = streaks.record_solve(old_state, today)
    points = points_for(problem.difficulty)
    try:
        await users.record_solve(
            bot.db, interaction.user.id, today, submission.solved_at, new_state, points
        )
    except users.AlreadySolved:
        current = streaks.displayed_streak(old_state, today)
        await interaction.followup.send(
            f"You've already been counted for today. Streak: {current}"
        )
        return

    # Success
    embed = discord.Embed(
        title=f"✅ {problem.title}",
        url=problem.url,
        description=f"{interaction.user.mention} solved today's problem!",
        color=DIFFICULTY_COLORS.get(problem.difficulty, discord.Color.blurple()),
    )
    embed.add_field(name="Points", value=f"+{points}")
    embed.add_field(name="🔥 Streak", value=str(new_state.current))
    embed.add_field(name="Longest", value=str(new_state.longest))
    embed.set_footer(text=f"Daily problem: {problem.date}")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="streak", description="Show your streak and stats")
@app_commands.describe(member="Whose stats to show (default: you)")
async def streak(
    interaction: discord.Interaction, member: discord.Member | None = None
):
    target = member or interaction.user
    user = await users.get_user(bot.db, target.id)

    if user is None:
        if target == interaction.user:
            text = "You haven't linked a LeetCode account yet. Use `/link` first."
        else:
            text = f"{target.display_name} hasn't linked a LeetCode account yet."
        await interaction.response.send_message(text, ephemeral=True)
        return
    if target == interaction.user:
        await remember_member(interaction)

    today = datetime.now(timezone.utc).date()
    state = users.row_to_streak_state(user)
    current = streaks.displayed_streak(state, today)
    total = await users.count_solves(bot.db, target.id)
    solved_today = state.last_solved == today

    embed = discord.Embed(
        title=f"{target.display_name}'s stats",
        url=f"https://leetcode.com/u/{user['leetcode_name']}/",
        color=discord.Color.orange() if current > 0 else discord.Color.greyple(),
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="🔥 Current streak", value=f"{current} days")
    embed.add_field(name="🏆 Longest streak", value=f"{state.longest} days")
    embed.add_field(name="⭐ Points", value=str(user["points"]))
    embed.add_field(name="✅ Total solved", value=str(total))
    embed.add_field(name="Today", value="Solved" if solved_today else "Not yet")
    embed.set_footer(text=f"LeetCode: {user['leetcode_name']}")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="setup", description="Choose the channel for the daily problem")
@app_commands.describe(channel="Channel where the daily problem gets posted")
@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):
    perms = channel.permissions_for(interaction.guild.me)
    if not (perms.view_channel and perms.send_messages and perms.embed_links):
        await interaction.response.send_message(
            f"I can't post in {channel.mention}. I need **View Channel**, "
            "**Send Messages** and **Embed Links** there.",
            ephemeral=True,
        )
        return

    await guilds.set_channel(bot.db, interaction.guild.id, channel.id)
    await interaction.response.send_message(
        f"Done! The daily problem will be posted in {channel.mention}.", ephemeral=True
    )


MEDALS = ["🥇", "🥈", "🥉"]


@bot.tree.command(name="leaderboard", description="Top 10 in this server")
@app_commands.describe(by="Rank by current streak or by total points")
@app_commands.choices(
    by=[
        app_commands.Choice(name="Streak", value="streak"),
        app_commands.Choice(name="Points", value="points"),
    ]
)
@app_commands.guild_only()
async def leaderboard(
    interaction: discord.Interaction, by: app_commands.Choice[str] | None = None
):
    ranking = by.value if by else "streak"
    today = datetime.now(timezone.utc).date()
    rows = await guilds.leaderboard(bot.db, interaction.guild.id, today, by=ranking)

    if not rows:
        await interaction.response.send_message(
            "Nobody here has linked a LeetCode account yet. Use `/link` to be the first!"
        )
        return

    lines = []
    for i, row in enumerate(rows):
        rank = MEDALS[i] if i < len(MEDALS) else f"`#{i + 1}`"
        lines.append(
            f"{rank} <@{row['discord_id']}> · 🔥 {row['streak']} · ⭐ {row['points']}"
        )

    embed = discord.Embed(
        title=f"🏆 Leaderboard · by {ranking}",
        description="\n".join(lines),
        color=discord.Color.gold(),
    )
    embed.set_footer(text=interaction.guild.name)
    await interaction.response.send_message(embed=embed)


#automatic daily post

POST_TIME = time(hour=0, minute=5, tzinfo=timezone.utc)  # LeetCode switches at 00:00 UTC
POST_MESSAGE = "📅 **New daily problem!** Solve it on LeetCode, then run `/solved`."


async def fetch_todays_problem(retries: int = 3, delay: int = 60) -> DailyProblem | None:
    """Fetch the daily problem, retrying until LeetCode shows today's date."""
    today = datetime.now(timezone.utc).date().isoformat()
    for attempt in range(1, retries + 1):
        try:
            problem = await fetch_daily(bot.http_session)
            if problem.date == today:
                return problem
            print(f"[post] LeetCode still shows {problem.date}, expected {today}")
        except LeetCodeError as e:
            print(f"[post] attempt {attempt}/{retries}: {e}")
        if attempt < retries:
            await asyncio.sleep(delay)
    return None


async def send_to_channel(channel_id: int, embed: discord.Embed) -> None:
    """Send an embed to a channel id (raises discord.HTTPException on failure)."""
    channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
    await channel.send(content=POST_MESSAGE, embed=embed)


async def post_daily_to_all() -> None:
    """Post today's problem in every configured channel that didn't get it yet."""
    problem = await fetch_todays_problem()
    if problem is None:
        print("[post] Giving up for now: today's problem not available")
        return
    await save_daily_problem(bot.db, problem)
    embed = build_daily_embed(problem)

    sent = 0
    for guild_id, channel_id in await guilds.all_channels(bot.db):
        if await posts.was_posted(bot.db, guild_id, problem.date):
            continue
        try:
            await send_to_channel(channel_id, embed)
        except discord.HTTPException as e:  # includes Forbidden and NotFound
            print(f"[post] guild {guild_id}, channel {channel_id}: {e}")
            continue  # one broken server must not stop the others
        await posts.mark_posted(bot.db, guild_id, problem.date)
        sent += 1
    print(f"[post] Daily problem {problem.date} posted in {sent} channel(s)")


@tasks.loop(time=POST_TIME)
async def daily_post_loop():
    try:
        await post_daily_to_all()
    except Exception as e:  # noqa: BLE001 - an unhandled error would stop the loop for good
        print(f"[post] Unexpected error: {e!r}")


@daily_post_loop.before_loop
async def before_daily_post_loop():
    await bot.wait_until_ready()
    try:
        await post_daily_to_all()  # catch up if the bot was offline at post time
    except Exception as e:  # noqa: BLE001 - must not prevent the loop from starting
        print(f"[post] Unexpected error on startup: {e!r}")


@bot.tree.command(name="postnow", description="Post today's problem in the /setup channel now (admin)")
@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
async def postnow(interaction: discord.Interaction):
    channel_id = await guilds.get_channel(bot.db, interaction.guild.id)
    if channel_id is None:
        await interaction.response.send_message(
            "No channel configured yet. Run `/setup` first.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    try:
        problem = await fetch_daily(bot.http_session)
        await send_to_channel(channel_id, build_daily_embed(problem))
    except LeetCodeError as e:
        print(f"[postnow] {e}")
        await interaction.followup.send("Couldn't reach LeetCode right now.")
        return
    except discord.HTTPException as e:
        print(f"[postnow] {e}")
        await interaction.followup.send(f"Couldn't post in <#{channel_id}>: {e.text}")
        return

    await interaction.followup.send(f"Posted in <#{channel_id}>.")


if __name__ == "__main__":
    bot.run(TOKEN)
