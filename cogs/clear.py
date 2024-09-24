import os
import logging

import discord
from discord.ext import commands

class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="clear", description="Clear matches category.")
    @commands.has_permissions(administrator=True)
    async def clear(self, ctx):
        if ctx.guild and ctx.guild.id == os.getenv("GUILD_ID") and ctx.author.guild_permissions.administrator:
            category = discord.utils.get(ctx.guild.categories, id=1246836714958487654)
            for channel in category.channels:
                try:
                    await channel.delete()
                except Exception as err:
                    logging.error(f"Error occured: {err}")

                    await ctx.send("An unexpected error occured.")
                    return

            await ctx.send("Done!")

async def setup(bot):
    await bot.add_cog(Clear(bot))
