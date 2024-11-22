import os
import logging
import asyncio

import pymysql
from pymysql.err import MySQLError

from steamwebapi.api import ISteamUser

import discord
from discord.ext import commands, tasks

from opengsq.protocols import Source

from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

double_check = []
@tasks.loop(minutes=5)
async def ping_database():
    bot.database.ping(reconnect=True)

    with bot.database.cursor() as cursor:
        cursor.execute("""SELECT ip, active FROM status WHERE active = 1""")
        server_list = cursor.fetchall()

        for (ip, active) in server_list:
            data = ip.split(":")
            try:
                source = Source(host=data[0], port=int(data[1]))
                info = await source.get_info()
                
                if info.players == 0:
                    if ip in double_check:
                        double_check.remove(ip)

                        query = "UPDATE status SET active = 0 WHERE ip = %s" 
                        cursor.execute(query, (ip,))

                        bot.database.commit()
                    else:
                        double_check.append(ip)
            except Exception as err:
                query = "UPDATE status SET active = 0 WHERE ip = %s"
                cursor.execute(query, (ip,))

                bot.database.commit()

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
