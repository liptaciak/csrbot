import os
import logging

import discord
from discord.ext import commands

class Top(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="top", description="Display 10 best players.")
    async def top(self, ctx):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")):
            try:
                with self.bot.database.cursor() as cursor:
                    cursor.execute("""SELECT name, points, matchs, wins FROM Players ORDER BY points DESC LIMIT 10""")
                    leaderboard = cursor.fetchall()
                    
                    top_embed = discord.Embed(color=0x5865F2, description="", title="TOP 10 PLAYERS IN CS:R")

                    for rank, (name, points, matchs, wins) in enumerate(leaderboard, start=1):
                        try:
                            winrate = (wins // matchs) * 100
                        except Exception:
                            winrate = 0

                        top_embed.description += f"{rank}. *{name}* - ELO: {points}, Matches: {matchs}, Wins: {wins}\n"

                    await ctx.send(embed=top_embed)
            except Exception as err:
                logging.error(f"Error occured: {err}")
                
                error_embed = discord.Embed(title="Error", description="An error occured while retrieving users from database.", color=0xDA373C)
                error_embed.set_footer(text="Please wait until you use this command again.")

                await ctx.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Top(bot))
