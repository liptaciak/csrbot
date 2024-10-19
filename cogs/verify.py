import os
import logging

from steamwebapi.api import IPlayerService

import discord
from discord.ext import commands

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="verify", description="Verify player.")
    @commands.has_permissions(administrator=True)
    async def verify(self, ctx, userid, steamid64):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")) and ctx.author.guild_permissions.administrator:
            try:
                with self.bot.database.cursor() as cursor:
                    query = "SELECT steam64 FROM Banned WHERE steam64 = %s"
                    cursor.execute(query, (str(steamid64),))

                    if cursor.fetchone():
                        await ctx.send("This user is banned.")
                    else:
                        query = "SELECT * FROM Players WHERE idDiscord = %s OR steam64 = %s"
                        cursor.execute(query, (str(userid), str(steamid64)))

                        if cursor.fetchone():
                            await ctx.send("This user is already verified.")
                        else:
                            member = ctx.guild.get_member(int(userid))
                            if member:
                                query = """INSERT INTO Players (idDiscord, steam64, points, name, matchs, wins, death, kills, adr) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""

                                role = ctx.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID")))
                                if role:
                                    await member.add_roles(role)

                                    cursor.execute(query, (userid, steamid64, 1000, member.name, 0, 0, 0, 0, 0.0))
                                    self.bot.database.commit()

                                    await ctx.send("This person has been sucessfully verified.")
                                else:
                                    await ctx.send("An unexpected error occured.")
                            else:
                                await ctx.send("Cannot find member.")
            except discord.NotFound:
                await ctx.send("Cannot find member.")
            except Exception as err:
                logging.error(f"Error occured: {err}")

                await ctx.send("An unexpected error occured.")

    @commands.hybrid_command(name="unverify", description="Delete player from database.")
    @commands.has_permissions(administrator=True)
    async def unverify(self, ctx, userid):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")) and ctx.author.guild_permissions.administrator:
            try:
                with self.bot.database.cursor() as cursor:
                    query = "SELECT * FROM Players WHERE idDiscord = %s"
                    cursor.execute(query, (str(userid),))

                    if not cursor.fetchone():
                        await ctx.send("This user is not verified.")
                    else:
                        member = ctx.guild.get_member(int(userid))
                        if member:
                            query = """DELETE FROM Players WHERE idDiscord = %s"""

                            role = ctx.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID")))
                            if role:
                                await member.remove_roles(role)
                                
                                cursor.execute(query, (str(userid),))
                                self.bot.database.commit()

                                await ctx.send("This person has been sucessfully removed from database.")
                            else:
                                await ctx.send("An unexpected error occured.")
                        else:
                            await ctx.send("Cannot find member.")
            except discord.NotFound:
                await ctx.send("Cannot find member.")
            except Exception as err:
                logging.error(f"Error occured: {err}")
                await ctx.send("An unexpected error occured.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.name.startswith("ticket-"):
            if message.content.startswith("https://steamcommunity.com/"):
                steamid = self.bot.steamapi.resolve_vanity_url(message.content)["response"]
                if steamid["message"] != "No match":
                    await message.channel.send(content=f"{steamid}")
                else:
                    await message.channel.send(content="Could not find user.")

async def setup(bot):
    await bot.add_cog(Verify(bot))
