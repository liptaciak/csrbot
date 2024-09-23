import os
import logging

import discord
from discord.ext import commands

class Matchmaking(commands.Cogs):
    def __init__(self, bot):
        self.bot = bot

        self.matches = {
                1245390449456447640: { "users": [], "state": "pre-search", "message": 0 }
        }

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        queue_embed = discord.Embed(color=0x808080, title="In queue: 0/10", description="")
         
        if after.channel and after.channel.id in self.matches:
            if after.channel.id != before.channel.id:
                if self.matches[after.channel.id]["state"] == "pre-search":
                    queue_msg = await member.guild.get_channel(1245416428442484777).send(embed=queue_embed)

                    self.matches[after.channel.id]["message"] = queue_msg.id
                    self.matches[after.channel.id]["state"] = "search"

                if member.id not in self.matches[after.channel.id]["users"]: 
                    if len(self.matches[after.channel.id]["users"]) < 10: 
                        self.matches[after.channel.id]["users"].append(member.id)

                        if len(self.matches[after.channel.id]["users"]) == 10:
                            accept_embed = discord.Embed(color=0x808080, title="The queue has filled up!", description="*Click on :white_check_mark: to accept, you have 30 seconds!*")
                            
                            message = await member.guild.get_channel(1245416428442484777).fetch_message(self.matches[after.channel.id]["message"]) 
                            await message.edit(embed=accept_embed)
                            
                            self.matches[after.channel.id]["state"] = "accept"
                            await message.add_reaction('✅')

                else:
                    if before.channel and before.channel.id in self.matches:
                        if len(self.matches[before.channel.id]["users"]) > 0 and member.id in self.matches[before.channel.id]["users"]:
                            self.matches[before.channel.id]["users"].remove(member.id)
                            
                            if len(self.matches[before.channel.id]["users"]) < 10 and self.matches[before.channel.id]["state"] == "accept":
                                self.matches[before.channel.id]["state"] = "search"
                            
