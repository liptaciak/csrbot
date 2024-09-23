import os
import logging

import discord
from discord.ext import commands

class Unban(commands.Cogs):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="unban", description="Unban player by SteamID64 using his DiscordID.")
    @commands.has_permissions(administrator=True)
    async def unban(self, ctx, id):
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
                            await member.add_roles(member.guild.get_role(1245409035948265622))

                            query = "SELECT steam64 FROM Banned WHERE steam64 = %s"
                            cursor.execute(query, (str(steam64),))

                            if cursor.fetchone():
                                cursor.execute("DELETE FROM Banned WHERE steam64 = %s", (str(steam64),))
                                
                                await ctx.send("The user got successfully unbanned.")
                            else:
                                await ctx.send("This user is not banned.")
                        else:
                            await ctx.send("User not found.")
                    else:
                        await ctx.send("The user is not in the database.")
            except Exception as err:
                logging.error(f"Error occured: {err}")

                await ctx.send("An unexpected error occured.")
