import os
import logging
import asyncio

import discord
from discord.ext import commands

from valve.rcon import RCON, RCONError

class Matchmaking(commands.Cogs):
    def __init__(self, bot):
        self.bot = bot

        self.matches = {
                1245390449456447640: {
                    "map": "de_cache",
                    "users": {}, 
                    "groups": {},
                    "state": "pre-search", 
                    "message": None 
                }
        }
    
    class AcceptView(discord.ui.View):
        def __init__(self, matchmaking):
            super().__init__()
            self.matchmaking = matchmaking

        @discord.ui.button(emoji=discord.PartialEmoji(name="white_check_mark"), label="Accept", style=discord.ButtonStyle.success)
        async def accept_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
            for match_id, match_data in self.matchmaking.matches.items():
                if match_data["message"] == interaction.message.id and match_data["state"] == "accept":
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
                    discord.SelectOption(label="Cache", value="de_cache", emoji=discord.PartialEmoji(name="de_cache", id=1245790208142737548)),
                    discord.SelectOption(label="Dust 2", value="de_dust2", emoji=discord.PartialEmoji(name="de_dust2", id=1245790212886495343)),
                    discord.SelectOption(label="Inferno", value="de_inferno", emoji=discord.PartialEmoji(name="de_inferno", id=1245790232796987444)),
                    discord.SelectOption(label="Mirage", value="de_mirage", emoji=discord.PartialEmoji(name="de_mirage", id=1245790217739436032)),
                    discord.SelectOption(label="Nuke", value="de_nuke", emoji=discord.PartialEmoji(name="de_nuke", id=1245789136523362456)),
                    discord.SelectOption(label="Nuke Old", value="de_nuke_old", emoji=discord.PartialEmoji(name="de_nuke_old", id=1246167328446746664)),
                    discord.SelectOption(label="Overpass", value="de_overpass", emoji=discord.PartialEmoji(name="de_overpass", id=1245790237532356689)),
                    discord.SelectOption(label="Seaside", value="de_seaside", emoji=discord.PartialEmoji(name="de_seaside", id=1281026580554059868)),
                    discord.SelectOption(label="Train", value="de_train", emoji=discord.PartialEmoji(name="de_train", id=1245790222730526823)),
                    discord.SelectOption(label="Vertigo", value="de_vertigo", emoji=discord.PartialEmoji(name="de_vertigo", id=1259159498858168430))
                ]
            ))
                          
    @discord.ui.select(placeholder="Choose a map...")
    async def map_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        selected_map = select.values[0]
        
        for match_id, match_data in self.matchmaking.matches.items():
            if match_data["message"] == interaction.message.id and match_data["state"] == "map":
                match = match_data
        
        if match and interaction.user.id in match["users"]:
            match["users"][interaction.user.id]["vote"] = selected_map

            if sum(1 for user in match["users"] if user["vote"] != None) == 10:
                ready_embed = discord.Embed(color=0x808080, title="Preparing server...", description="*This can take up to 2-3 minutes*")

                message = await interaction.user.guild.get_channel(os.getenv("QUEUE_CHANNEL_ID")).fetch_message(match["message"]) 
                await message.edit(embed=ready_embed, view=None)

                match["state"] = "preparing"
                
                with self.matchmaking.bot.database.cursor() as cursor:
                    team_ct = []
                    team_t = []

                    data = ""

                    for id, user in list(match["users"].items())[:5]:
                        query = "SELECT steam64 FROM Players WHERE idDiscord = %s"

                        cursor.execute(query, (str(id),))
                        row = cursor.fetchall()

                        team_ct.append(id)
                        
                        if row:
                            match["users"][id]["steamid"] = row[0]
                            data += str(row[0]) + "C\n"

                    for id, user in list(match["users"].items())[5:10]:
                        query = "SELECT steam64 FROM Players WHERE idDiscord = %s"

                        cursor.execute(query, (str(id),))
                        row = cursor.fetchall()

                        team_t.append(id)
                        
                        if row:
                            match["users"][id]["steamid"] = row[0]
                            data += str(row[0]) + "T\n"

                    data -= "\n"

                    file = open("./csgo/addons/sourcemod/configs/whitelist.txt", "w")
                    file.write(data)
                    
                    file.close()
                
                ports = os.getenv("SERVER_PORTS").split(",");
                
                for port in ports:
                    await asyncio.sleep(1.5)
                    
                    try: 
                        with RCON((os.getenv("SERVER_IP"), int(port)), os.getenv("RCON_PASS")) as rcon:
                            result = rcon(f'sm_setupmatch {match["map"]} "team_{match["users"][0]}" "team_{match["users"][5]}"')
                            logging.info(f"Match created: {result}")
                    except (RCONError, ConnectionResetError, ConnectionRefusedError) as err:
                        logging.error(f"RCON Error occured on port {port}: {err}")
                        continue
                    
                    if result != "Active\n":
                        server_port = port
                        break
                    else:
                        logging.info(f"Port {port} is active!")
                        continue

                await asyncio.sleep(60.0)

                embed_ready = discord.Embed(title=f'**The server is ready! team_{match["users"][0]} VS team_{match["users"][5]}**', description="The server is Ready! GLHF!", color = 0x808080)
                
                embed_ready.add_field(name="**IP**", value=f'`{str(os.getenv("SERVER_IP"))}:{str(server_port)}``', inline=True)

                embed_ready.add_field(name="**Map**", value=f'{match["map"]}', inline=True)
                embed_ready.add_field(name="**Server Location**", value=":flag_de: Germany, Falkenstein", inline=True)

                
                embed_ready.add_field(name=f'CT **team_{match["users"][0]}**', value=team_ct, inline=True)
                embed_ready.add_field(name=f'T **team_{match["users"][5]}**', value=team_t, inline=True)

                embed_ready.set_footer(text="If all players don't connect in 5 minutes, the server will be shut down.")
                
                for id, user in list(match["users"].items()):
                    user = self.matchmaking.bot.get_guild(int(os.getenv("GUILD_ID"))).query_members(user_ids=[id])
                    
                    await user[0].move_to(channel=None)

                match = {
                    "map": "de_cache",
                    "users": {}, 
                    "groups": {},
                    "state": "pre-search", 
                    "message": None 
                }

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
                        self.matches[after.channel.id]["users"][member.id] = { "team": None, "steamid": None, "accepted": False, "vote": None }

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
                            
