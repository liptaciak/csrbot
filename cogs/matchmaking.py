import os
import logging

import discord
from discord.ext import commands

class Matchmaking(commands.Cogs):
    def __init__(self, bot):
        self.bot = bot

        self.matches = {
                1245390449456447640: {
                    "map": "",
                    "users": {}, 
                    "state": "pre-search", 
                    "message": 0 
                }
        }
    
    class AcceptView(discord.ui.View):
        def __init__(self, matchmaking):
            super().__init__()
            self.matchmaking = matchmaking

        @discord.ui.button(emoji=discord.PartialEmoji(name=":white_check_mark:"), label="Accept", style=discord.ButtonStyle.success)
        async def accept_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
            for match_id, match_data in self.matchmaking.matches.items():
                if match_data["message"] == interaction.message.id:
                    match = match_data

            if match and interaction.user.id in match["users"]:
                if match["users"][interaction.user.id]["accepted"] == False:
                    match["users"][interaction.user.id]["accepted"] = True
                    
                if sum(1 for user in match["users"].values() if user["accepted"]) == 10:
                    map_embed = discord.Embed(color=0x808080, title="Choose a map", description="*Click on icon to select. You have 30 seconds!*")
                    map_view = self.matchmaking.MapView(self.matchmaking)
                    
                    message = await interaction.user.guild.get_channel(os.getenv("QUEUE_CHANNEL_ID")).fetch_message(match["message"]) 
                    await message.edit(embed=map_embed, view=map_view)
                    match["state"] = "map"

    class MapView(discord.ui.View):
        def __init__(self, matchmaking):
            super().__init__()
            self.matchmaking = matchmaking
            self.add_item(discord.ui.Select(
                placeholder="Choose a map...",
                options=[
                    discord.SelectOption(label="Mirage", value="de_mirage", emoji=discord.PartialEmoji(name="de_mirage", id=1245790217739436032)),
                    discord.SelectOption(label="Dust 2", value="de_dust2", emoji=discord.PartialEmoji(name="de_dust2", id=1245790212886495343)),
                    discord.SelectOption(label="Seaside", value="de_seaside", emoji=discord.PartialEmoji(name="de_seaside", id=1281026580554059868)),
                    discord.SelectOption(label="Nuke", value="de_nuke", emoji=discord.PartialEmoji(name="de_nuke", id=1245789136523362456)),
                    discord.SelectOption(label="Cache", value="de_cache", emoji=discord.PartialEmoji(name="de_cache", id=1245790208142737548)),
                    discord.SelectOption(label="Inferno", value="de_inferno", emoji=discord.PartialEmoji(name="de_inferno", id=1245790232796987444)),
                    discord.SelectOption(label="Overpass", value="de_overpass", emoji=discord.PartialEmoji(name="de_overpass", id=1245790237532356689)),
                    discord.SelectOption(label="Train", value="de_train", emoji=discord.PartialEmoji(name="de_train", id=1245790222730526823)),
                    discord.SelectOption(label="Nuke Old", value="de_nuke_old", emoji=discord.PartialEmoji(name="de_nuke_old", id=1246167328446746664))
                ]
            ))
                          
    @discord.ui.select(placeholder="Choose a map...")
    async def map_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        selected_map = select.values[0]
        
        # TODO: FINISH MAP SELECTION
        pass
 
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        queue_embed = discord.Embed(color=0x808080, title="In queue: 0/10", description="")
        
        if after.channel and after.channel.id in self.matches:
            for user in after.channel.members:
                if user.id != member.id and user.id not in self.matches[after.channel.id]["users"]:
                    await user.move_to(channel=None)

            if after.channel.id != before.channel.id:
                if self.matches[after.channel.id]["state"] == "pre-search":
                    queue_msg = await member.guild.get_channel(os.getenv("QUEUE_CHANNEL_ID")).send(embed=queue_embed)

                    self.matches[after.channel.id]["message"] = queue_msg.id
                    self.matches[after.channel.id]["state"] = "search"

                if member.id not in self.matches[after.channel.id]["users"]: 
                    if len(self.matches[after.channel.id]["users"]) < 10 and self.matches[after.channel.id]["state"] == "search": 
                        self.matches[after.channel.id]["users"][member.id] = { "accepted": False, "voted": False }

                        if len(self.matches[after.channel.id]["users"]) == 10:
                            accept_embed = discord.Embed(color=0x808080, title="The queue has filled up!", description="*Click on :white_check_mark: to accept, you have 30 seconds!*")
                            accept_view = self.AcceptView(self)
                            
                            message = await member.guild.get_channel(os.getenv("QUEUE_CHANNEL_ID")).fetch_message(self.matches[after.channel.id]["message"]) 
                            await message.edit(embed=accept_embed, view=accept_view)
                            
                            self.matches[after.channel.id]["state"] = "accept"

                else:
                    if before.channel and before.channel.id in self.matches:
                        if len(self.matches[before.channel.id]["users"]) > 0 and member.id in self.matches[before.channel.id]["users"] and self.matches[before.channel.id]["state"] == "search":
                            self.matches[before.channel.id]["users"].remove(member.id)
                            
