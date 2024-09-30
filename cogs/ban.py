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
                            await ctx.send("Cannot find user in the server.")
                            return

                        logging.info(f"Found member: {member.id} with SteamID64: {steam64}")

                        role = member.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID"))) 
                        if role:
                            await member.remove_roles(role)
                        else:
                            await ctx.send("The role to remove was not found.")
                            return

                        query = "SELECT * FROM Banned WHERE steam64 = %s"
                        cursor.execute(query, (steam64,))

                        if cursor.fetchone():
                            await ctx.send("This user is already banned.")
                        else:
                            query = "INSERT INTO Banned (steam64) VALUES (%s)"
                            cursor.execute(query, (steam64,))
                            self.bot.database.commit()

                            await ctx.send("The user was successfully banned.")
                    else:
                        await ctx.send("This person is not in the database.")
            except Exception as err:
                logging.error(f"Error occurred: {err}")
                await ctx.send(f"An unexpected error occurred: {err}")
        else:
            await ctx.send("You do not have permission to use this command or are in the wrong guild.")

async def setup(bot):
    await bot.add_cog(Ban(bot))
