import os

import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

from bot.services.leetcode import LeetCodeError, fetch_daily

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")

if TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN missing. Did you create the .env file?")


class DailyCodeBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)  # slash commands registry
        self.http_session: aiohttp.ClientSession | None = None

    async def setup_hook(self):  # send command list to Discord
        self.http_session = aiohttp.ClientSession()

        if DEV_GUILD_ID:
            guild = discord.Object(id=int(DEV_GUILD_ID))

            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

            print(f"Commands synced to development guild {DEV_GUILD_ID}")
        else:
            await self.tree.sync()
            print("Global commands synced")

    async def close(self):
        if self.http_session:
            await self.http_session.close()
        await super().close()

    async def on_ready(self):
        print(f"Logged in as {self.user} | ID: {self.user.id}")


bot = DailyCodeBot()


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    print(
        f"[error] /{interaction.command.name if interaction.commad else '?'}: {error!r}"
    )
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


@bot.tree.command(name="daily", description="Show today's LeetCode problem")
async def daily(interaction: discord.Interaction):
    await interaction.response.defer()  # 15 mins to send the answer

    try:
        problem = await fetch_daily(bot.http_session)
    except LeetCodeError as e:
        print(f"[daily] {e}")
        await interaction.followup.send(
            "Couldn't reach LeetCode right now. Try again later."
        )
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


if __name__ == "__main__":
    bot.run(TOKEN)
