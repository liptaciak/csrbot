import os
import logging

import discord
from discord.ext import commands

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="rank", description="Get rank of user.")
    async def rank(self, ctx, member: discord.Member = None):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")):
            player = member or ctx.author

            try:
                with self.bot.database.cursor() as cursor:
                    query = "SELECT points, steam64, matchs, wins, kills, death FROM Players WHERE idDiscord = %s"
                    cursor.execute(query, (player.id,))

                    row = cursor.fetchone()
                    if row:
                        elo = int(row[0])
                        
                        ranks = [
                            (3000, 9, "<:lvl10:1255948786623057961>"), (2400, 8, "<:lvl9:1255948818239848499>"), 
                            (2100, 7, "<:lvl8:1255948834614411324>"), (1800, 6, "<:lvl7:1255948849525293118>"), 
                            (1500, 5, "<:lvl6:1255948866407239752>"), (1200, 4, "<:lvl5:1255948882882596946>"), 
                            (900, 3, "<:lvl4:1255948899408019509>"), (600, 2, "<:lvl3:1255948919561650306>"),  
                            (300, 1, "<:lvl2:1255948935365791754>"), (0, 0, "<:lvl1:1255948950494773372>"), 
                        ]
                        
                        user_rank = next(rank for min_elo, rank, _ in ranks if elo >= min_elo)
                        kd = float(row[4]) / float(row[5]) if float(row[5]) != 0 else 0.0
                        avg = float(row[4]) / float(row[2]) if float(row[2]) != 0 else 0.0

                        rank_embed = discord.Embed(color=0x808080, title=f"{ranks[user_rank][2]} {player.name} stats!", description=f"```py\nELO: {row[0]}\nLevel: {user_rank + 1}\nMatches: {row[2]}\nWins: {row[3]}\nKDR: {kd}\nAVG: {avg}\nSteamID64: {row[1]}```")
                        
                        query = "SELECT FirstDay FROM Awards WHERE steam64 = %s"
                        cursor.execute(query, (row[1]))

                        award_row = cursor.fetchone()
                        if award_row:
                            if int(award_row[0]) == 1:
                                rank_embed += "\n<:FirstDayMedal:1255950280374091898>"

                        await ctx.send(embed=rank_embed)
                    else:
                        await ctx.send("You or the member you listed is not in the database.")
            except Exception as err:
                logging.error(f"Error occured: {err}")

                await ctx.send("An unexpected error occured.")

async def setup(bot):
    await bot.add_cog(Rank(bot))
