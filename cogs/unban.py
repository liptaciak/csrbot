import os
import logging

import discord
from discord.ext import commands

class Unban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="unban", description="Unban player by SteamID64 using his DiscordID.")
    @commands.has_permissions(administrator=True)
    async def unban(self, ctx, id):
        if not ctx.guild:
            error_embed = discord.Embed(title="Error", description="This command can only be used in a server.", color=0xDA373C)
            await ctx.send(embed=error_embed)

            return
        
        guild_id = os.getenv("GUILD_ID")
        if not guild_id:
            error_embed = discord.Embed(title="Error", description="GUILD_ID environment variable is not set.", color=0xDA373C)
            await ctx.send(error_embed)

            return
        
        if ctx.guild.id == int(guild_id) and ctx.author.guild_permissions.administrator:
            try:
                with self.bot.database.cursor() as cursor:
                    query = "SELECT steam64 FROM Players WHERE idDiscord = %s"
                    cursor.execute(query, (id,))
                    
                    rows = cursor.fetchone()
                    if rows:
                        steam64 = rows[0]

                        member = ctx.guild.get_member(int(id))
                        if not member:
                            error_embed = discord.Embed(title="Error", description="Cannot find user in this server.", color=0xDA373C)
                            await ctx.send(embed=error_embed)

                            return

                        role = member.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID")))
                        if not role:
                            error_embed = discord.Embed(title="Error", description="The role to add was not found.", color=0xDA373C)
                            await ctx.send(embed=error_embed)

                            return
                        
                        await member.add_roles(role)

                        query = "SELECT steam64 FROM Banned WHERE steam64 = %s"
                        cursor.execute(query, (str(steam64),))

                        if cursor.fetchone():
                            cursor.execute("DELETE FROM Banned WHERE steam64 = %s", (str(steam64),))
                            self.bot.database.commit()

                            success_embed = discord.Embed(title="Success", description="The user was successfully unbanned.", color=0x248046)
                            await ctx.send(embed=success_embed)
                        else:
                            error_embed = discord.Embed(title="Error", description="This user is not banned.", color=0xDA373C)
                            await ctx.send(embed=error_embed)
                    else:
                        error_embed = discord.Embed(title="Error", description="The user is not in the database.", color=0xDA373C)
                        await ctx.send(embed=error_embed)
            except Exception as err:
                logging.error(f"Error occurred: {err}")

                error_embed = discord.Embed(title="Error", description="An unexpected error occured.", color=0xDA373C)
                await ctx.send(embed=error_embed)
        else:
            error_embed = discord.Embed(title="Error", description="You do not have permission to use this command or are in the wrong guild.", color=0xDA373C)
            await ctx.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Unban(bot))
