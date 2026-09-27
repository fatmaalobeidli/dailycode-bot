import os

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")

if TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN missing. Did you create the .env file?")

class DailyCodeBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self) #slash commands registry

    async def setup_hook(self): #send command list to Discord
        if DEV_GUILD_ID:
            guild = discord.Object(id=int(DEV_GUILD_ID))

            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

            print(f"Commands synced to development guild {DEV_GUILD_ID}")
        else:
            await self.tree.sync()
            print("Global commands synced")

    async def on_ready(self):
        print(f"Logged in as {self.user} | ID: {self.user.id}")

bot = DailyCodeBot()


@bot.tree.command(name="ping", description="Check if the bot is alive") #/ping

async def ping(interaction: discord.Interaction):
    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! {latency_ms} ms")


bot.run(TOKEN)