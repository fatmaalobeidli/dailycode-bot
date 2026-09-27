import os

import aiohttp
import aiosqlite
import discord
from discord import app_commands
from dotenv import load_dotenv

from bot.db import init_db
from bot.repositories.users import LeetCodeNameTaken, link_user
from bot.services.leetcode import LeetCodeError, fetch_daily, user_exists

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
        if self.http_session:
            await self.http_session.close()
        if self.db: 
            await self.db.close()
        await super().close()

    async def on_ready(self):
        print(f"Logged in as {self.user} | ID: {self.user.id}")


bot = DailyCodeBot()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    command = interaction.command.name if interaction.command else "?"
    print(f"[error] /{command}: {error!r}")
    message = "Something went wrong. Please try again later."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)  # only user who ran cmd sees the msg
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


@bot.tree.command(name="daily", description="Show today's LeetCode problem")
async def daily(interaction: discord.Interaction):
    await interaction.response.defer()  # 15 mins to send the answer instead of 3 s

    try:
        problem = await fetch_daily(bot.http_session)
    except LeetCodeError as e:
        print(f"[daily] {e}")
        await interaction.followup.send("Couldn't reach LeetCode right now. Try again later.")
        return

    embed = discord.Embed(
        title=problem.title,
        url=problem.url,
        color=DIFFICULTY_COLORS.get(problem.difficulty, discord.Color.blurple()),
    )

    embed.add_field(name="Difficulty", value=problem.difficulty)
    embed.add_field(name="Acceptance", value=f"{problem.ac_rate}%")
    if problem.tags:
        embed.add_field(name="Topics", value=", ".join(problem.tags), inline=False)
    embed.set_footer(text=f"Daily problem: {problem.date}")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="link", description="Link your LeetCode account")
@app_commands.describe(username="Your LeetCode username")
async def link(interaction: discord.Interaction, username: str):
    await interaction.response.defer(ephemeral=True)
    username = username.strip()

    try:
        exists = await user_exists(bot.http_session, username)
    except LeetCodeError as e:
        print(f"[link] {e}")
        await interaction.followup.send("Couldn't reach LeetCode right now. Try again later.")
        return

    if not exists:
        await interaction.followup.send(f"LeetCode user **{username}** doesn't exist. Check the spelling.")
        return

    try:
        await link_user(bot.db, interaction.user.id, username)
    except LeetCodeNameTaken:
        await interaction.followup.send(f"**{username}** is already linked to another Discord account.")
        return

    await interaction.followup.send(f"Linked to LeetCode account **{username}**.")


if __name__ == "__main__":
    bot.run(TOKEN)
