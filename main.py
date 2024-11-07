import os
import logging
import asyncio

import pymysql
from pymysql.err import MySQLError

from steamwebapi.api import ISteamUser

import discord
from discord.ext import commands, tasks

from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@tasks.loop(minutes=5)
async def ping_database():
    bot.database.ping(reconnect=True)
    print("Database pinged.")

@bot.event
async def on_ready():
    print(f"\nLogged in as: {bot.user.name} ({bot.user.id}).")
    
    await bot.tree.sync()

    try:
        bot.steamapi = ISteamUser(steam_api_key=os.getenv("STEAM_API_KEY"))
        print("\nSuccessfully connected to SteamAPI.")
    except Exception as err:
        logging.error(f"There was an error connecting to SteamAPI: {err}")

    try:
        bot.database = pymysql.connect(
            host = os.getenv("DB_HOST"),
            password = os.getenv("DB_PASS"),
            port = int(os.getenv("DB_PORT")),
            database = os.getenv("DB_NAME"),
            user = os.getenv("DB_USER")
        )
        
        print("Connected to MySQL database.\n")
        ping_database.start()
    except MySQLError as err:
        logging.error(f"Error while connecting to database: {err}")

        await bot.close()

@bot.event
async def on_disconnect():
    if bot.database:
        bot.database.close()

        logging.info("Successfully disconnected from database.")

cogs = [
    "cogs.top", "cogs.ban", 
    "cogs.rank", "cogs.verify", 
    "cogs.unban", "cogs.cancel_match",
    "cogs.status", "cogs.matchmaking",
]

async def setup_bot():
    for cog in cogs:
        await bot.load_extension(cog)
        print(f"{cog} loaded.")

    await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(setup_bot())
