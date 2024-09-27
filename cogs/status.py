import os
import logging
import asyncio

import discord
from discord.ext import commands

from valve.rcon import RCON, RCONError

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="status", description="Info about server status.")
    @commands.has_permissions(administrator=True)
    async def status(self, ctx):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")) and ctx.author.guild_permissions.administrator:
            ports = os.getenv("SERVER_PORTS").split(",")

            msg = await ctx.send("Loading...")
            status_embed = discord.Embed(color=0x808080, title="Server status")
            
            active = 0
            for port in ports:
                await asyncio.sleep(1.5)
                try:
                    with RCON((os.getenv("SERVER_IP"), int(port)), os.getenv("RCON_PASS")) as rcon:
                        rcon("say Server is active!")

                        status_embed.add_field(name=f"**Server {port}**", value=":green_circle: Active\n", inline=True)
                        active += 1
                except (RCONError, ConnectionResetError, ConnectionRefusedError) as err:
                    logging.error(f"RCON Error occured on port {port}: {err}")
                    status_embed.add_field(name=f"**Server {port}**", value=":red_circle: Not Active\n", inline=True)
            
            status_embed.title = f"Server status: {active}/{len(ports)} active."
            await msg.edit(embed=status_embed, content="")  

async def setup(bot):
    await bot.add_cog(Status(bot))
