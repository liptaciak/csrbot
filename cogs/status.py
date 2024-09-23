import os
import logging
import asyncio

import discord
from discord.ext import commands

from valve.rcon import RCON, RCONError

class Status(commands.Cogs):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="status", description="Info about server status.")
    @commands.has_permissions(administrator=True)
    async def status(self, ctx):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")) and ctx.author.guild_permissions.administrator:
            ports = [26125, 26250, 26375, 26500, 26625, 26750, 26875, 27000, 27015, 27020]

            msg = await ctx.send("Loading...")
            status_embed = discord.Embed(color=0x808080, title="Server status")

            for port in ports:
                await asyncio.sleep(1.5)
                try:
                    with RCON((os.getenv("SERVER_IP"), port), os.getenv("RCON_PASS")) as rcon:
                        rcon("say Server is active!")
                        status_embed.add_field(name=f"**SERVER {port}**", value=":green_circle: | Active", inline=True)
                except (RCONError, ConnectionResetError, ConnectionRefusedError) as err:
                    logging.error(f"RCON Error occured on port {port}: {err}")
                    status_embed.add_field(name=f"**SERVER {port}**", value=":red_circle: | Not Active", inline=True)

            await msg.edit(embed=status_embed, content="")  
