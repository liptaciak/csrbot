import os
import asyncio

import pymysql
from pymysql.connections import MySQLError

import discord
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user.name} ({bot.user.id}).")

    try:
        bot.database = pymysql.connect(
            host = os.getenv("DB_HOST"),
            password = os.getenv("DB_PASS"),
            port = int(os.getenv("DB_PORT")),
            database = os.getenv("DB_NAME"),
            user = os.getenv("DB_USER")
        )

        print("Connected to database.")
    except MySQLError as err:
        print(f"Error while connecting to database: {err}")

        await bot.close()

@bot.event
async def on_disconnect():
    if bot.database:
        bot.database.close()

        print("Successfully disconnected from database.")

cogs = ["cogs.top", "cogs.rank", "cogs.verify", "cogs.cancel_match"]

async def setup_bot():
    for cog in cogs:
        await bot.load_extension(cog)

    await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(setup_bot())
