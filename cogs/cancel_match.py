import os 
import logging
import asyncio

import discord
from discord.ext import commands

from valve.rcon import RCON, RCONError

class CancelMatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="cancelmatch", description="Cancel match.")
    @commands.has_permissions(administrator=True)
    async def cancelmatch(ctx, server_port):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")) and ctx.author.guild_permissions.administrator:
            error_embed = discord.Embed(color=0xFF0000, title="Error cancelling match.", description="An error occured while cancelling match.")

            try:
                await asyncio.sleep(1.5)
                with RCON((os.getenv("SERVER_IP"), int(server_port)), os.getenv("RCON_PASS")) as rcon:
                    rcon("sm_cancel_match")

                cancel_embed = discord.Embed(color=0x808080, title=f"Match #{server_port} canceled.", description="Have a good day.")
                await ctx.send(embed=cancel_embed)
            except RCONError as err:
                logging.error(f"RCON Error occured: {err}")

                await ctx.send(embed=error_embed)
            except Exception as err:
                logging.error(f"Unexpected error occured: {err}")

                await ctx.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(CancelMatch(bot))
