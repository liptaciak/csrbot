import os
import logging

import discord
from discord.ext import commands

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ban", description="Ban player by SteamID64 using DiscordID")
    @commands.has_permissions(administrator=True)
    async def ban(self, ctx, userid):
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
        
        guild_id = os.getenv("GUILD_ID")
        if not guild_id:
            await ctx.send("GUILD_ID environment variable is not set.")
            return

        if ctx.guild.id == int(guild_id) and ctx.author.guild_permissions.administrator:
            try:
                with self.bot.database.cursor() as cursor:
                    query = "SELECT steam64 FROM Players WHERE idDiscord = %s"
                    cursor.execute(query, (userid,))

                    rows = cursor.fetchone()
                    if rows:
                        steam64 = rows[0]

                        member = ctx.guild.get_member(int(userid))
                        if not member:
                            error_embed = discord.Embed(title="Error", description="Cannot find user in the server.", color=0xDA373C)
                            await ctx.send(embed=error_embed)

                            return

                        role = member.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID"))) 
                        if role:
                            await member.remove_roles(role)
                        else:
                            error_embed = discord.Embed(title="Error", description="The role to remove was not found.", color=0xDA373C)
                            await ctx.send(embed=error_embed)
                            return

                        query = "SELECT * FROM Banned WHERE steam64 = %s"
                        cursor.execute(query, (steam64,))

                        if cursor.fetchone():
                            error_embed = discord.Embed(title="Error", description="This user is already banned.", color=0xDA373C)
                            await ctx.send(embed=error_embed)
                        else:
                            query = "INSERT INTO Banned (steam64) VALUES (%s)"
                            cursor.execute(query, (steam64,))
                            self.bot.database.commit()
                            
                            success_embed = discord.Embed(title="Success", description="The user was successfully banned.", color=0x248046)
                            await ctx.send(embed=success_embed)
                    else:
                        error_embed = discord.Embed(title="Error", description="This person is not in the database.", color=0xDA373C)
                        await ctx.send(embed=error_embed)
            except Exception as err:
                logging.error(f"Error occurred: {err}")

                error_embed = discord.Embed(title="Error", description="An unexpected error occured.", color=0xDA373C)
                await ctx.send(embed=error_embed)
        else:
            error_embed = discord.Embed(title="Error", description="You do not have permission to use this command or are in the wrong guild.", color=0xDA373C)
            await ctx.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Ban(bot))
