import os 
import logging
import asyncio

import discord
from discord.ext import commands

from valve.rcon import RCON, RCONError

class CancelMatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="cancel", description="Cancel match.")
    @commands.has_permissions(administrator=True)
    async def cancel(self, ctx, server):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")) and ctx.author.guild_permissions.administrator:
            error_embed = discord.Embed(color=0xDA373C, title="Error", description="An error occured while cancelling the match.")
            error_embed.set_footer(text="Check if the IP you provided is correct.")
            
            server_data = server.split(":")
            try:
                await asyncio.sleep(1.5)
                with RCON((server_data[0], int(server_data[1])), os.getenv("RCON_PASS")) as rcon:
                    rcon("sm_cancel_match")

                cancel_embed = discord.Embed(color=0x248046, title="Success", description=f"Match {server} has been successfully cancelled. Have a good day.")
                cancel_embed.set_footer(text="Players will not lose or gain any ELO.")

                await ctx.send(embed=cancel_embed)
            except RCONError as err:
                logging.error(f"RCON Error occured: {err}")

                await ctx.send(embed=error_embed)
            except Exception as err:
                logging.error(f"Unexpected error occured: {err}")

                await ctx.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(CancelMatch(bot))
