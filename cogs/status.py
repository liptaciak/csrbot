import os
import logging

import discord
from discord.ext import commands

from opengsq.protocols import Source

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="status", description="Info about server status.")
    @commands.has_permissions(administrator=True)
    async def status(self, ctx):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")) and ctx.author.guild_permissions.administrator:
            status_embed = discord.Embed(title="CS:R Server Status", description="", color=0x5865F2)
            servers_active = 0

            players_active = 0
            players_max = 0

            with self.bot.database.cursor() as cursor:
                cursor.execute("""SELECT ip, active FROM status""")
                server_list = cursor.fetchall()
                
                for (ip, active) in server_list:
                    data = ip.split(":")
                    
                    if active == 1:
                        try:
                            source = Source(host=data[0], port=int(data[1]))
                            info = await source.get_info()

                            value = f":green_circle: Active players: {info.players}/{info.max_players}."
                            servers_active += 1

                            players_active += info.players
                            players_max += info.max_players
                        except Exception as e:
                            logging.error(f"Failed to get info for server {ip}: {e}")
                            value = ":red_circle: Can't fetch status."
                    else:
                        value = ":yellow_circle: Server inactive."

                    status_embed.add_field(name=f"**{ip}**", value=value, inline=True)
            
                status_embed.description = f"Servers {servers_active}/{len(server_list)} active. Players: {players_active}/{players_max} active."
                status_embed.set_footer(text="This is the state of ongoing match on the server, not if its down.")

                await ctx.send(embed=status_embed)

async def setup(bot):
    await bot.add_cog(Status(bot))
