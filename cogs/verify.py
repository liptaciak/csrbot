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
                        error_embed = discord.Embed(title="Error", description="This user is banned.", color=0xDA373C)
                        await ctx.send(embed=error_embed)
                    else:
                        query = "SELECT * FROM Players WHERE idDiscord = %s OR steam64 = %s"
                        cursor.execute(query, (str(userid), str(steamid64)))

                        if cursor.fetchone():
                            error_embed = discord.Embed(title="Error", description="This user is already verified.", color=0xDA373C)
                            await ctx.send(embed=error_embed)
                        else:
                            member = ctx.guild.get_member(int(userid))
                            if member:
                                query = """INSERT INTO Players (idDiscord, steam64, points, name, matchs, wins, death, kills) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""

                                role = ctx.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID")))
                                if role:
                                    await member.add_roles(role)

                                    cursor.execute(query, (userid, steamid64, 1000, member.name, 0, 0, 0, 0, 0.0))
                                    self.bot.database.commit()
                                    
                                    success_embed = discord.Embed(title="Success", description="This person has been successfully verified.", color=0x248046)
                                    await ctx.send(embed=success_embed)
                                else:
                                    error_embed = discord.Embed(title="Error", description="An unexpected error occured.", color=0xDA373C)
                                    await ctx.send(embed=error_embed)
                            else:
                                error_embed = discord.Embed(title="Error", description="Cannot find member in this server.", color=0xDA373C)
                                await ctx.send(embed=error_embed)
            except discord.NotFound:
                error_embed = discord.Embed(title="Error", description="Cannot find member in this server.", color=0xDA373C)
                await ctx.send(embed=error_embed)
            except Exception as err:
                logging.error(f"Error occured: {err}")
                
                error_embed = discord.Embed(title="Error", description="An unexpected error occured.", color=0xDA373C)
                await ctx.send(embed=error_embed)

    @commands.hybrid_command(name="unverify", description="Delete player from database.")
    @commands.has_permissions(administrator=True)
    async def unverify(self, ctx, userid):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")) and ctx.author.guild_permissions.administrator:
            try:
                with self.bot.database.cursor() as cursor:
                    query = "SELECT * FROM Players WHERE idDiscord = %s"
                    cursor.execute(query, (str(userid),))

                    if not cursor.fetchone():
                        error_embed = discord.Embed(title="Error", description="This user is not verified.", color=0xDA373C)
                        await ctx.send(embed=error_embed)
                    else:
                        member = ctx.guild.get_member(int(userid))
                        if member:
                            query = """DELETE FROM Players WHERE idDiscord = %s"""

                            role = ctx.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID")))
                            if role:
                                await member.remove_roles(role)
                                
                                cursor.execute(query, (str(userid),))
                                self.bot.database.commit()
                                
                                success_embed = discord.Embed(title="Success", description="This person has been successfully removed from the database.", color=0x248046)
                                await ctx.send(embed=success_embed)
                            else:
                                error_embed = discord.Embed(title="Error", description="An unexpected error occured.", color=0xDA373C)
                                await ctx.send(embed=error_embed)
                        else:
                            error_embed = discord.Embed(title="Error", description="Cannot find member in this server.", color=0xDA373C)
                            await ctx.send(embed=error_embed)
            except discord.NotFound:
                error_embed = discord.Embed(title="Error", description="Cannot find member in this server.", color=0xDA373C)
                await ctx.send(embed=error_embed)
            except Exception as err:
                logging.error(f"Error occured: {err}")

                error_embed = discord.Embed(title="Error", description="An unexpected error occured.", color=0xDA373C)
                await ctx.send(embed=error_embed)

    #@commands.Cog.listener()
    #async def on_message(self, message: discord.Message):
    #    if message.channel.name.startswith("ticket-"):
    #        if message.content.startswith("https://steamcommunity.com/"):
    #            steamid = self.bot.steamapi.resolve_vanity_url(message.content)["response"]
    #            if steamid["message"] != "No match":
    #                await message.channel.send(content=f"{steamid}")
    #            else:
    #                await message.channel.send(content="Could not find user.")
    
    @commands.Cog.listener()
    async def on_member_remove(member: discord.Member):
        with self.bot.database.cursor() as cursor:
            query = "SELECT * FROM Players WHERE idDiscord = %s"
            cursor.execute(query, (str(member.id),))

            if cursor.fetchone():
                query = "DELETE FROM Players WHERE idDiscord = %s"
                cursor.execute(query, (str(member.id),))

                self.bot.database.commit()

    @commands.Cog.listener()
    async def on_member_ban(guild: discord.Guild, user: discord.Member):
        with self.bot.database.cursor() as cursor:
            query = "SELECT steam64 FROM Players WHERE idDiscord = %s"
            cursor.execute(query, (str(user.id),))
            
            result = cursor.fetchone()
            if result:
                query = "DELETE FROM Players WHERE idDiscord = %s"
                cursor.execute(query, (str(user.id),))

                self.bot.database.commit()

                query = "SELECT * FROM Banned WHERE steam64 = %s"
                cursor.execute(query, (str(result[0]),))
                if not cursor.fetchone():
                    query = "INSERT INTO Banned (steam64) VALUES (%s)"
                    cursor.execute(query, (str(result[0]),))

                    self.bot.database.commit()

    @commands.Cog.listener()
    async def on_user_update(before: discord.Member, after: discord.Member):
        if before.name != after.name:
            with self.bot.database.cursor() as cursor:
                query = "SELECT name FROM Players WHERE idDiscord = %s"
                cursor.execute(query, (str(after.id),))

                if cursor.fetchone():
                    query = "UPDATE Players SET name = %s WHERE idDiscord = %s"
                    cursor.execute(query, (after.name, str(after.id)))
                    self.bot.database.commit()

async def setup(bot):
    await bot.add_cog(Verify(bot))
