import os
import logging
import asyncio

from collections import Counter

import discord
from discord.ext import commands

from valve.rcon import RCON, RCONError

class Matchmaking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.matches = {
                1281757327204159501: {
                    "max": 4,
                    "map": "de_cache",
                    "users": {}, 
                    "groups": {},
                    "state": "pre-search", 
                    "message": None 
                }
        }
    
    class AcceptView(discord.ui.View):
        def __init__(self, matchmaking):
            super().__init__(timeout=30)
            self.matchmaking = matchmaking

        @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
        async def accept_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            for match_id, match_data in self.matchmaking.matches.items():
                if interaction.message and match_data["message"] == interaction.message.id and match_data["state"] == "accept":
                    match = match_data

            if match and interaction.user.id in match["users"]:
                if match["users"][interaction.user.id]["accepted"] == False:
                    match["users"][interaction.user.id]["accepted"] = True
                    
                    await interaction.response.send_message("Match accepted!", ephemeral=True)
                    
                if sum(1 for user in match["users"].values() if user["accepted"]) == match["max"]:
                    map_embed = discord.Embed(color=0x808080, title="Choose a map", description="*Click on icon to select. You have 30 seconds!*")
                    map_view = self.matchmaking.MapView(self.matchmaking)

                    message = await interaction.user.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(match["message"]) 
                    await message.edit(embed=map_embed, view=map_view)

                    match["state"] = "map"

        async def on_timeout(self):
            match = None 

            for match_id, match_data in self.matchmaking.matches.items():
                if match_data["state"] == "accept":
                    match = match_data

            if match:
                if sum(1 for user in match["users"].values() if user["accepted"]) < match["max"]:
                    match["state"] = "search"
                    
                    not_accepted = []

                    for user in match["users"]:
                        if user["accepted"] == False:
                            not_accepted.append(user)

                            member = self.matchmaking.bot.get_guild(int(os.getenv("GUILD_ID"))).query_members(user_ids=match["users"][user]) 
                            await member[0].move_to(channel=None)
                        else:
                            match["users"][user]["accepted"] = False

                    for user in not_accepted:
                        match["users"].pop(user)

                    queue_embed = discord.Embed(color=0x808080, title=f'In queue: {len(match["users"])}/4', description="")
                    
                    index = 1
                    for user in match["users"]:
                        queue_embed.description += f"{index}. {match["users"][user]["name"]}\n"
                        index += 1

                    message = await self.matchmaking.bot.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(match["message"]) 
                    await message.edit(embed=queue_embed, view=None) 

    class MapView(discord.ui.View):
        def __init__(self, matchmaking):
            super().__init__(timeout=30)
            self.matchmaking = matchmaking

        @discord.ui.select(
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
        )
        async def map_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
            selected_map = select.values[0]
            await interaction.response.send_message(f"Your choice: {selected_map}", ephemeral=True)

            for match_id, match_data in self.matchmaking.matches.items():
                if match_data["message"] == interaction.message.id and match_data["state"] == "map":
                    match = match_data

            if match and interaction.user.id in match["users"]:
                match["users"][interaction.user.id]["vote"] = selected_map

                if sum(1 for user in match["users"].values() if user["vote"] is not None) == match["max"]:
                    ready_embed = discord.Embed(color=0x808080, title="Preparing server...", description="*This can take up to 2-3 minutes*")

                    message = await interaction.user.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(match["message"]) 
                    await message.edit(embed=ready_embed, view=None)
                    
                    votes = [user["vote"] for user in match["users"].values()]
                    vote_count = Counter(votes)
                    max_votes = max(vote_count.values())

                    maps = [map for map, count in vote_count.items() if count == max_votes]
                    match["map"] = maps[0]

                    await self.matchmaking.prepare_server(match)

        async def on_timeout(self):
            for match_id, match_data in self.matchmaking.matches.items():
                if match_data["state"] == "map":
                    match = match_data

            if match:
                votes = [user["vote"] for user in match["users"] if user["vote"] != None]
                vote_count = Counter(votes)
                max_votes = max(vote_count.values())

                maps = [map for map, count in vote_count.items() if count == max_votes]
                match["map"] = maps[0]

                await self.matchmaking.prepare_server(match)

    async def prepare_server(match):
        match["state"] = "preparing"
                    
        with self.bot.database.cursor() as cursor:
            team_ct = []
            team_t = []

            data = ""

            for id, user in list(match["users"].items())[:2]:
                query = "SELECT steam64 FROM Players WHERE idDiscord = %s"

                cursor.execute(query, (str(id),))
                row = cursor.fetchall()

                team_ct.append(id)
                
                if row:
                    match["users"][id]["steamid"] = row[0]
                    data += str(row[0]) + "C\n"

            for id, user in list(match["users"].items())[2:4]:
                query = "SELECT steam64 FROM Players WHERE idDiscord = %s"

                cursor.execute(query, (str(id),))
                row = cursor.fetchall()

                team_t.append(id)
                
                if row:
                    match["users"][id]["steamid"] = row[0]
                    data += str(row[0]) + "T\n"

            file = open("./csgo/addons/sourcemod/configs/whitelist.txt", "w")
            file.write(data)
            
            file.close()
        
        ports = os.getenv("SERVER_PORTS").split(",");
        
        for port in ports:
            await asyncio.sleep(1.5)
            
            try: 
                with RCON((os.getenv("SERVER_IP"), int(port)), os.getenv("RCON_PASS")) as rcon:
                    result = rcon(f'sm_setupmatch {match["map"]} "team_{match["users"][0]["name"]}" "team_{match["users"][1]["name"]}"')
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

        embed_ready = discord.Embed(title=f'**The server is ready! team_{match["users"][0]["name"]} VS team_{match["users"][1]["name"]}**', description="The server is Ready! GLHF!", color = 0x808080)
        
        embed_ready.add_field(name="**IP**", value=f'`{str(os.getenv("SERVER_IP"))}:{str(server_port)}``', inline=True)

        embed_ready.add_field(name="**Map**", value=f'{match["map"]}', inline=True)
        embed_ready.add_field(name="**Server Location**", value=":flag_de: Germany, Falkenstein", inline=True)

        
        embed_ready.add_field(name=f'CT **team_{match["users"][0]["name"]}**', value=team_ct, inline=True)
        embed_ready.add_field(name=f'T **team_{match["users"][1]["name"]}**', value=team_t, inline=True)

        embed_ready.set_footer(text="If all players don't connect in 5 minutes, the server will be shut down.")
        
        for id, user in list(match["users"].items()):
            user = self.matchmaking.bot.get_guild(int(os.getenv("GUILD_ID"))).query_members(user_ids=[id])
            
            await user[0].move_to(channel=None)

        match = {
            "max": 10,
            "map": "de_cache",
            "users": {}, 
            "groups": {},
            "state": "pre-search", 
            "message": None 
        }

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        queue_embed = discord.Embed(color=0x808080, title="In queue: 0/4", description="")
        
        if after.channel and after.channel.id in self.matches or before.channel and before.channel.id in self.matches:
            if after.channel:
                for user in after.channel.members:
                    if user.id != member.id and user.id not in self.matches[after.channel.id]["users"]:
                        await user.move_to(channel=None)

            if before.channel == None or after.channel and after.channel.id != before.channel.id:
                if self.matches[after.channel.id]["state"] == "pre-search":
                    queue_msg = await member.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).send(embed=queue_embed)

                    self.matches[after.channel.id]["message"] = queue_msg.id
                    self.matches[after.channel.id]["state"] = "search"

                if after.channel and member.id not in self.matches[after.channel.id]["users"]: 
                    if len(self.matches[after.channel.id]["users"]) < self.matches[after.channel.id]["max"] and self.matches[after.channel.id]["state"] == "search": 
                        self.matches[after.channel.id]["users"][member.id] = { "name": member.name, "team": None, "steamid": None, "accepted": False, "vote": None }

                        message = await member.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(self.matches[after.channel.id]["message"])
                        
                        queue_embed.title = f'In queue: {len(self.matches[after.channel.id]["users"])}/4'
                        
                        index = 1
                        for user in self.matches[after.channel.id]["users"]:
                            queue_embed.description += f"{index}. {self.matches[after.channel.id]["users"][user]["name"]}\n"
                            index += 1

                        await message.edit(embed=queue_embed)

                        if len(self.matches[after.channel.id]["users"]) == self.matches[after.channel.id]["max"]:
                            accept_embed = discord.Embed(color=0x808080, title="The queue has filled up!", description="*Click on :white_check_mark: to accept, you have 30 seconds!*")
                            accept_view = self.AcceptView(self)
                            
                            await message.edit(embed=accept_embed, view=accept_view)
                                 
                            self.matches[after.channel.id]["state"] = "accept"
            else:
                if before.channel and before.channel.id in self.matches:
                    if len(self.matches[before.channel.id]["users"]) > 0 and member.id in self.matches[before.channel.id]["users"] and self.matches[before.channel.id]["state"] == "search":
                        self.matches[before.channel.id]["users"].pop(member.id)
                        
                        message = await member.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(self.matches[before.channel.id]["message"])
                        
                        queue_embed = discord.Embed(color=0x808080, description="")
                        queue_embed.title = f'In queue: {len(self.matches[before.channel.id]["users"])}/4'
                        
                        index = 1
                        for user in self.matches[before.channel.id]["users"]:
                            queue_embed.description += f"{index}. {self.matches[before.channel.id]["users"][user]["name"]}\n"
                            index += 1

                        await message.edit(embed=queue_embed)

async def setup(bot):
    await bot.add_cog(Matchmaking(bot))
