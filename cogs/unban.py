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
                    cursor.execute(query, (id,))
                    
                    rows = cursor.fetchone()
                    if rows:
                        steam64 = rows[0]

                        member = ctx.guild.get_member(int(id))
                        if not member:
                            await ctx.send("User not found in the server.")
                            return

                        logging.info(f"Found member: {member.id} with SteamID64: {steam64}")

                        role = member.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID")))
                        if not role:
                            await ctx.send("The role to add was not found.")
                            return
                        
                        await member.add_roles(role)

                        query = "SELECT steam64 FROM Banned WHERE steam64 = %s"
                        cursor.execute(query, (str(steam64),))

                        if cursor.fetchone():
                            cursor.execute("DELETE FROM Banned WHERE steam64 = %s", (str(steam64),))
                            await ctx.send("The user was successfully unbanned.")
                        else:
                            await ctx.send("This user is not banned.")
                    else:
                        await ctx.send("The user is not in the database.")
            except Exception as err:
                logging.error(f"Error occurred: {err}")
                await ctx.send(f"An unexpected error occurred: {err}")
        else:
            await ctx.send("You do not have permission to use this command or are in the wrong guild.")

async def setup(bot):
    await bot.add_cog(Unban(bot))
