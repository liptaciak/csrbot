import os
import logging

import discord
from discord.ext import commands

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ban", description="Ban player by SteamID64 using DiscordID")
    @commands.has_permissions(administrator=True)
    async def ban(self, ctx, id):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")) and ctx.author.guild_permissions.administrator:
            try:
                with self.bot.database.cursor() as cursor:
                    query = "SELECT steam64 FROM Players WHERE idDiscord = %s"
                    cursor.execute(query, (id,))

                    rows = cursor.fetchone()
                    if rows:
                        steam64 = rows[0]
                        member = ctx.guild.get_member(int(id))

                        if member:
                            await member.remove_roles(member.guild.get_role(1245409035948265622))

                            query = "SELECT * FROM Banned WHERE steam64 = %s"
                            cursor.execute(query, (steam64,))

                            if cursor.fetchone():
                                await ctx.send("This user is already banned.")
                            else:
                                query = "INSERT INTO Banned (steam64) VALUES (%s)"
                                cursor.execute(query, (steam64,))

                                await ctx.send("The user got sucessfully banned.")
                        else:
                            await ctx.send("Cannot find user.")
                    else:
                        await ctx.send("This person is not in the database.")
            except Exception as err:
                logging.error(f"Error occured: {err}")

                await ctx.send("An unexpected error occured.")
