import os 
import json
import logging
import asyncio

from collections import Counter
from datetime import timedelta
from time import time

import discord
from discord.ext import commands

from valve.rcon import RCON, RCONError

class Matchmaking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.matches = {
                1281757327204159501: {
                    "max": 10,
                    "region": "eu",
                    "map": "de_cache",
                    "users": {}, 
                    "groups": {},
                    "state": "pre-search", 
                    "message": None,
                    "id": None,
                    "timestamp": 0,
                },
                1294055233609011355: {
                    "max": 10,
                    "region": "na",
                    "map": "de_cache",
                    "users": {},
                    "groups": {},
                    "state": "pre-search",
                    "message": None,
                    "id": None,
                    "timestamp": 0,
                }
        }

        self.awaiting_accept = {}

    class ConnectView(discord.ui.View):
        def __init__(self, init_link: str):
            super().__init__()

            self.button = discord.ui.Button(label="Connect", url=init_link)
            self.add_item(self.button)

    class AcceptView(discord.ui.View):
        def __init__(self, matchmaking, timeout=30):
            super().__init__(timeout=None)
            self.timeout_duration = timeout
            self.is_timed_out = False

            self.matchmaking = matchmaking
        
        async def start_timer(self):
            await asyncio.sleep(self.timeout_duration)
            self.is_timed_out = True

            await self.on_timeout_custom()
            
        async def on_timeout_custom(self):
            match = None 

            for match_id, match_data in self.matchmaking.matches.items():
                if match_data["state"] == "accept":
                    match = match_data

            if match:
                if sum(1 for user in match["users"].values() if user["accepted"]) < match["max"]:
                    match["state"] = "search"
                    
                    not_accepted = []
                    not_accepted_ping = ""

                    for user in match["users"]:
                        if match["users"][user]["accepted"] == False:
                            not_accepted.append(user)
                        else:
                            match["users"][user]["accepted"] = False

                    for user in not_accepted:
                        match["users"].pop(user)

                        for group in match["groups"]:
                            if user in match["groups"][group]:
                                match["groups"][group].remove(user)

                        not_accepted_ping += f"<@{user}> "

                        member = await self.matchmaking.bot.get_guild(int(os.getenv("GUILD_ID"))).query_members(user_ids=[user]) 
                        await member[0].move_to(channel=None)

                        if not member[0].guild_permissions.administrator:
                            await member[0].timeout(timedelta(minutes=3))

                    queue_embed = discord.Embed(color=0x5865F2, title=f'In queue: {len(match["users"])}/{match["max"]}', description="")
                    queue_embed.set_footer(text="The search channel will be locked when it reaches max size.")

                    index = 1
                    for user in match["users"]:
                        queue_embed.description += f"{index}. {match["users"][user]["name"]}\n"
                        index += 1
                    
                    channel = self.matchmaking.bot.get_channel(match["id"])
                    role = self.matchmaking.bot.get_guild(int(os.getenv("GUILD_ID"))).get_role(int(os.getenv("VERIFIED_ROLE_ID")))

                    asyncio.create_task(self.matchmaking.revert_permissions(channel, role))
                    
                    channel = self.matchmaking.bot.get_channel(int(os.getenv("QUEUE_CHANNEL_ID")))

                    message = await channel.fetch_message(match["message"]) 
                    await message.delete()

                    queue_msg = await channel.send(content=f"{not_accepted_ping}failed to accept the match.", embed=queue_embed) 
                    match["message"] = queue_msg.id


        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if self.is_timed_out:
                return False
            return True

        @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
        async def accept_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            for match_id, match_data in self.matchmaking.matches.items():
                if interaction.message and match_data["message"] == interaction.message.id and match_data["state"] == "accept":
                    match = match_data

            if match and interaction.user.id in match["users"]:
                message = await interaction.user.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(match["message"]) 

                if match["users"][interaction.user.id]["accepted"] == False:
                    match["users"][interaction.user.id]["accepted"] = True
                    
                    await interaction.response.defer()
                
                accepted = sum(1 for user in match["users"].values() if user["accepted"])

                accepted_embed = discord.Embed(color=0x248046, title=f"The queue has filled up! Ending: <t:{match["timestamp"]}:R>", description=f"Users accepted: {accepted}/{match["max"]}\n")
                accepted_embed.set_footer(text="Click on button to accept, you have 30 seconds!")

                await message.edit(embed=accepted_embed)

                if accepted == match["max"]:
                    match["timestamp"] = int(time() + 20)

                    map_embed = discord.Embed(color=0x4E5058, title=f"Choose a map. Expires <t:{match["timestamp"]}:R>", description="")
                    map_embed.set_footer(text="You can change your vote. Click on icon to select. You have 20 seconds! ")
                    
                    map_embed.add_field(name="<:aztec:1291798839430217728> Aztec", value="Votes: 0", inline=True)
                    map_embed.add_field(name="<:cache:1289642476738707568> Cache", value="Votes: 0", inline=True)
                    map_embed.add_field(name="<:cbble:1289645106206609469> Cobblestone", value="Votes: 0", inline=True)
                    map_embed.add_field(name="<:dust2:1289645615881654292> Dust 2", value="Votes: 0", inline=True)
                    map_embed.add_field(name="<:inferno:1289645114729173103> Inferno", value="Votes: 0", inline=True)
                    map_embed.add_field(name="<:mirage:1289645111315140692> Mirage", value="Votes: 0", inline=True)
                    map_embed.add_field(name="<:nuke:1289645109058474004> Nuke", value="Votes: 0", inline=True)
                    map_embed.add_field(name="<:nuke_old:1289645103291302002> Nuke Old", value="Votes: 0", inline=True)
                    map_embed.add_field(name="<:overpass:1289645113051713649> Overpass", value="Votes: 0", inline=True)
                    map_embed.add_field(name="<:seaside:1289645101550665822> Seaside", value="Votes: 0", inline=True)
                    map_embed.add_field(name="<:trainn:1289645099030151218> Train", value="Votes: 0", inline=True)
                    map_embed.add_field(name="<:vertigo:1289645096328757369> Vertigo", value="Votes: 0", inline=True)

                    map_view = self.matchmaking.MapView(self.matchmaking, timeout=20)
                    asyncio.create_task(map_view.start_timer())

                    await message.edit(content=None, embed=map_embed, view=map_view)
                    match["state"] = "map"

    class MapView(discord.ui.View):
        def __init__(self, matchmaking, timeout=20):
            super().__init__(timeout=None)
            self.timeout_duration = timeout
            self.is_timed_out = False

            self.matchmaking = matchmaking
        
        async def start_timer(self):
            await asyncio.sleep(self.timeout_duration)
            self.is_timed_out = True
            await self.on_timeout_custom()
        
        async def on_timeout_custom(self):
            match = None

            for match_id, match_data in self.matchmaking.matches.items():
                if match_data["state"] == "map":
                    match = match_data

            if match:
                votes = [user["vote"] for user in match["users"].values()] 
                vote_count = Counter(votes)
                max_votes = max(vote_count.values())

                maps = [map for map, count in vote_count.items() if count == max_votes]

                if maps[0] != None:
                    match["map"] = maps[0]
                
                await self.matchmaking.prepare_server(match)

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if self.is_timed_out:
                return False
            return True

        @discord.ui.select(
            placeholder="Choose a map...",
            options=[
                discord.SelectOption(label="Aztec", value="de_aztec", emoji=discord.PartialEmoji(name="aztec", id=1291798839430217728)),
                discord.SelectOption(label="Cache", value="de_cache", emoji=discord.PartialEmoji(name="de_cache", id=1245790208142737548)),
                discord.SelectOption(label="Cobblestone", value="de_cbble", emoji=discord.PartialEmoji(name="de_cobblestone", id=1245790227973279775)),
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

            for match_id, match_data in self.matchmaking.matches.items():
                if match_data["message"] == interaction.message.id and match_data["state"] == "map":
                    match = match_data

            if match and interaction.user.id in match["users"]:
                match["users"][interaction.user.id]["vote"] = selected_map

                await interaction.response.defer()
                
                maps_embed = discord.Embed(color=0x4E5058, title=f"Choose a map. Expires <t:{match["timestamp"]}:R>", description="") 
                maps_embed.set_footer(text="You can change your vote. Click on icon to select. You have 20 seconds! ")
                
                vote_counts = {
                    "de_aztec": 0, "de_cache": 0, 
                    "de_cbble": 0, "de_dust2": 0, 
                    "de_inferno": 0, "de_mirage": 0, 
                    "de_nuke": 0, "de_nuke_old": 0,
                    "de_overpass": 0, "de_seaside": 0, 
                    "de_train": 0, "de_vertigo": 0
                }

                for user_vote in match["users"].values():
                    vote = user_vote.get("vote")

                    if vote in vote_counts:
                        vote_counts[vote] += 1
                
                maps_embed.add_field(name="<:aztec:1291798839430217728> Aztec", value=f'Votes: {vote_counts["de_aztec"]}', inline=True)
                maps_embed.add_field(name="<:cache:1289642476738707568> Cache", value=f'Votes: {vote_counts["de_cache"]}', inline=True)
                maps_embed.add_field(name="<:cbble:1289645106206609469> Cobblestone", value=f'Votes: {vote_counts["de_cbble"]}', inline=True)
                maps_embed.add_field(name="<:dust2:1289645615881654292> Dust 2", value=f'Votes: {vote_counts["de_dust2"]}', inline=True)
                maps_embed.add_field(name="<:inferno:1289645114729173103> Inferno", value=f'Votes: {vote_counts["de_inferno"]}', inline=True)
                maps_embed.add_field(name="<:mirage:1289645111315140692> Mirage", value=f'Votes: {vote_counts["de_mirage"]}', inline=True)
                maps_embed.add_field(name="<:nuke:1289645109058474004> Nuke", value=f'Votes: {vote_counts["de_nuke"]}', inline=True)
                maps_embed.add_field(name="<:nuke_old:1289645103291302002> Nuke Old", value=f'Votes: {vote_counts["de_nuke_old"]}', inline=True)
                maps_embed.add_field(name="<:overpass:1289645113051713649> Overpass", value=f'Votes: {vote_counts["de_overpass"]}', inline=True)
                maps_embed.add_field(name="<:seaside:1289645101550665822> Seaside", value=f'Votes: {vote_counts["de_seaside"]}', inline=True)
                maps_embed.add_field(name="<:trainn:1289645099030151218> Train", value=f'Votes: {vote_counts["de_train"]}', inline=True)
                maps_embed.add_field(name="<:vertigo:1289645096328757369> Vertigo", value=f'Votes: {vote_counts["de_vertigo"]}', inline=True)

                message = await interaction.user.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(match["message"]) 
                await message.edit(embed=maps_embed)

                if sum(1 for user in match["users"].values() if user["vote"] is not None) == match["max"]:
                    votes = [user["vote"] for user in match["users"].values()]
                    vote_count = Counter(votes)
                    max_votes = max(vote_count.values())

                    maps = [map for map, count in vote_count.items() if count == max_votes]
                    match["map"] = maps[0]
                    
                    await self.matchmaking.prepare_server(match)

    async def prepare_server(self, match):
        with self.bot.database.cursor() as cursor:
            team_ct = []
            team_t = []
            
            players = {}
            
            half = len(match["users"]) // 2
            for party in self.matches[match["id"]]["groups"]:
                user_keys = list(self.matches[match["id"]]["users"].keys())
                party_indices = [user_keys.index(player) for player in self.matches[match["id"]]["groups"][party] if player in user_keys]
                
                team_ct_indices = [i for i in party_indices if i < half]
                team_t_indices = [i for i in party_indices if i >= half]

                if len(team_ct_indices) == 0 or len(team_t_indices) == 0:
                    continue
                
                if len(team_ct_indices) > len(team_t_indices):
                    for idx in team_t_indices:
                        for swap_idx, swap_key in enumerate(self.matches[match["id"]]["users"].keys()):
                            if swap_idx >= half:
                                break

                            if swap_key not in self.matches[match["id"]]["groups"][party]:
                                temp_key = list(self.matches[match["id"]]["users"])[idx]
                                self.matches[match["id"]]["users"][swap_key], self.matches[match["id"]]["users"][temp_key] = \
                                    self.matches[match["id"]]["users"][temp_key], self.matches[match["id"]]["users"][swap_key]
                                break
                else:
                    for idx in team_ct_indices:
                        for swap_idx, swap_key in enumerate(self.matches[match["id"]]["users"].keys()):
                            if swap_idx < half:
                                continue

                            if swap_key not in self.matches[match["id"]]["groups"][party]:
                                temp_key = list(self.matches[match["id"]]["users"])[idx]
                                self.matches[match["id"]]["users"][swap_key], self.matches[match["id"]]["users"][temp_key] = \
                                    self.matches[match["id"]]["users"][temp_key], self.matches[match["id"]]["users"][swap_key]
                                break
                       
            index = 0
            for id, user in list(match["users"].items())[:half]:
                query = "SELECT steam64 FROM Players WHERE idDiscord = %s"

                cursor.execute(query, (str(id),))
                row = cursor.fetchone()

                team_ct.append(id)
                
                if row:
                    if index not in players:
                        players[index] = {}

                    players[index] = { "steamid": str(row[0]), "team": "C" }
                    match["users"][id]["steamid"] = row[0]

                index += 1

            for id, user in list(match["users"].items())[half:]:
                query = "SELECT steam64 FROM Players WHERE idDiscord = %s"

                cursor.execute(query, (str(id),))
                row = cursor.fetchone()

                team_t.append(id)
                
                if row:
                    if index not in players:
                        players[index] = {}

                    players[index] = { "steamid": str(row[0]), "team": "T" }
                    match["users"][id]["steamid"] = row[0]
                
                index += 1
            
            active_servers = []
            with self.bot.database.cursor() as cursor:
                query = "SELECT ip FROM status WHERE active = 0 AND region = %s"
                cursor.execute(query, (match["region"],))

                active_servers = cursor.fetchall()
            
            server_port = 0
            server_ip = ""
            for (server,) in active_servers:
                data = server.split(":")

                await asyncio.sleep(1.5)
                try: 
                    with RCON((data[0], int(data[1])), os.getenv("RCON_PASS")) as rcon:
                        try:
                            rcon(f'sm_setupmatch {match["map"]} "team_{match["users"][team_ct[0]]["name"]}" "team_{match["users"][team_t[0]]["name"]}"')
                            
                            print(f"Match created: {result}")
                            
                            server_port = int(data[1])
                            server_ip = server
                            break
                        except (RCONError, ConnectionResetError, ConnectionRefusedError) as err:
                            logging.error(f"RCON Error occured on {server}: {err}")
                            continue
                except Exception as err:
                    logging.error(f"Unexpected error on {server}: {err}")
                    continue
                   
            if server_port == 0:
                embed_error = discord.Embed(title="**Error**", description="Couldnt find any available servers. Please wait or contact an administrator.", color=0xDA373C)
            
                channel = self.bot.get_guild(int(os.getenv("GUILD_ID"))).get_channel(int(os.getenv("QUEUE_CHANNEL_ID")))
                message = await channel.fetch_message(match["message"]) 
            
                await message.delete()
                error_msg = await channel.send(content="<@830812204030623824> <@884172802679242823> <@953319088946544670>", embed=embed_error, view=None) 

                for id, user in list(match["users"].items()):
                    user = await self.bot.get_guild(int(os.getenv("GUILD_ID"))).query_members(user_ids=[id])
            
                    await user[0].move_to(channel=None)
            
                channel = self.bot.get_channel(match["id"])
                role = self.bot.get_guild(int(os.getenv("GUILD_ID"))).get_role(int(os.getenv("VERIFIED_ROLE_ID")))

                await channel.set_permissions(role, connect=False) 

                self.matches[match["id"]] = {
                    "max": match["max"],
                    "region": match["region"],
                    "map": "de_cache",
                    "users": {}, 
                    "groups": {},
                    "state": "pre-search", 
                    "message": None,
                    "id": None,
                }
            
                return

            query = "UPDATE whitelist SET players = %s WHERE ip = %s"
            cursor.execute(query, (json.dumps(players), server_ip))

            query = "UPDATE status SET active = 1 WHERE ip = %s"
            cursor.execute(query, (server_ip,))

            self.bot.database.commit()

            embed_ready = discord.Embed(title=f'**Preparing match team_{match["users"][team_ct[0]]["name"]} VS team_{match["users"][team_t[0]]["name"]}**', description="The server is being prepared... :hourglass:", color=0x4E5058)
            
            embed_ready.add_field(name="**IP**", value=f'``Preparing server...``', inline=True)

            embed_ready.add_field(name="**Map**", value=f'``{match["map"]}``', inline=True)
            if match["region"] == "eu":
                embed_ready.add_field(name="**Server Location**", value=":flag_de: Germany, Falkenstein", inline=True)
            else:
                embed_ready.add_field(name="**Server Location**", value=":flag_us: United States, Arizona", inline=True)
            
            ct_users = ""
            t_users = ""
            
            half = len(match["users"]) // 2

            index = 1
            for user_id in list(match["users"].keys())[:half]:
                user = match["users"][user_id]
                ct_users += f"{index}. {user['name']}\n"
                index += 1

            index = 1
            for user_id in list(match["users"].keys())[half:]:
                user = match["users"][user_id]
                t_users += f"{index}. {user['name']}\n"
                index += 1

            embed_ready.add_field(name=f'**team_{match["users"][team_ct[0]]["name"]}**', value=ct_users, inline=True)
            embed_ready.add_field(name=f'**team_{match["users"][team_t[0]]["name"]}**', value=t_users, inline=True)
            
            embed_ready.set_footer(text="This can take up to 1-2 minutes.")

            message = await self.bot.get_guild(int(os.getenv("GUILD_ID"))).get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(match["message"]) 
            await message.edit(embed=embed_ready, view=None)
 
            await asyncio.sleep(60.0)

        embed_ready = discord.Embed(title=f'**The server is ready! team_{match["users"][team_ct[0]]["name"]} VS team_{match["users"][team_t[0]]["name"]}**', description="The server is Ready! GLHF!", color = 0x4E5058)
        
        embed_ready.add_field(name="**IP**", value=f'``{server_ip}``', inline=True)

        embed_ready.add_field(name="**Map**", value=f'``{match["map"]}``', inline=True)
        embed_ready.add_field(name="**Server Location**", value=":flag_de: Germany, Falkenstein", inline=True)
        
        ct_users = ""
        t_users = ""
        
        half = len(match["users"]) // 2

        index = 1
        for user_id in list(match["users"].keys())[:half]:
            user = match["users"][user_id]
            ct_users += f"{index}. {user['name']}\n"
            index += 1

        index = 1
        for user_id in list(match["users"].keys())[half:]:
            user = match["users"][user_id]
            t_users += f"{index}. {user['name']}\n"
            index += 1

        embed_ready.add_field(name=f'**team_{match["users"][team_ct[0]]["name"]}**', value=ct_users, inline=True)
        embed_ready.add_field(name=f'**team_{match["users"][team_t[0]]["name"]}**', value=t_users, inline=True)

        embed_ready.set_footer(text="If all players don't connect in 5 minutes, the server will be shut down.")
        
        for id, user in list(match["users"].items()):
            user = await self.bot.get_guild(int(os.getenv("GUILD_ID"))).query_members(user_ids=[id])
            
            await user[0].move_to(channel=None)
        
        server_data = server_ip.split(":")
        connect_view = self.ConnectView(f"https://csrestored.xyz/connect.html?ip={server_data[0]}&port={server_data[1]}")

        message = await self.bot.get_guild(int(os.getenv("GUILD_ID"))).get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(match["message"])  
        
        player_pings = ""
        for user in match["users"]:
           player_pings += f"<@{user}> "

        new_message = await message.channel.send(content=player_pings, embed=embed_ready, view=connect_view)
        self.matches[match["id"]]["message"] = new_message.id
        
        await message.delete()

        channel = self.bot.get_channel(match["id"])
        role = self.bot.get_guild(int(os.getenv("GUILD_ID"))).get_role(int(os.getenv("VERIFIED_ROLE_ID")))

        asyncio.create_task(self.revert_permissions(channel, role))

        self.matches[match["id"]] = {
            "max": match["max"],
            "region": match["region"],
            "map": "de_cache",
            "users": {}, 
            "groups": {},
            "state": "pre-search", 
            "message": None,
            "id": None,
        }
        
    async def revert_permissions(self, channel, role):
        if self.matches[channel.id] and self.matches[channel.id]["state"] == "search" or self.matches[channel.id]["state"] == "pre-search":
            await asyncio.sleep(2.5)
            await channel.set_permissions(role, connect=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):        
        if after.channel and after.channel.id in self.matches or before.channel and before.channel.id in self.matches:
            if after.channel:
                for user in after.channel.members:
                    if user.id != member.id and user.id not in self.matches[after.channel.id]["users"]:
                        await user.move_to(channel=None)

            if before.channel == None or after.channel and after.channel.id != before.channel.id:
                queue_embed = discord.Embed(color=0x5865F2, title=f"In queue: 0/{self.matches[after.channel.id]["max"]}", description="")

                if self.matches[after.channel.id]["state"] == "pre-search":
                    queue_msg = await member.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).send(content="", embed=queue_embed)

                    self.matches[after.channel.id]["message"] = queue_msg.id
                    self.matches[after.channel.id]["state"] = "search"

                if after.channel and member.id not in self.matches[after.channel.id]["users"]: 
                    if len(self.matches[after.channel.id]["users"]) < self.matches[after.channel.id]["max"] and self.matches[after.channel.id]["state"] == "search": 
                        self.matches[after.channel.id]["users"][member.id] = { "id": member.id, "name": member.name, "team": None, "steamid": None, "accepted": False, "vote": None }

                        message = await member.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(self.matches[after.channel.id]["message"])
                        
                        queue_embed.title = f'In queue: {len(self.matches[after.channel.id]["users"])}/{self.matches[after.channel.id]["max"]}'
                        queue_embed.set_footer(text="The search channel will be locked when it reaches max size.")
                        
                        index = 1
                        for user in self.matches[after.channel.id]["users"]:
                            queue_embed.description += f"{index}. {self.matches[after.channel.id]["users"][user]["name"]}\n"

                            self.matches[after.channel.id]["id"] = after.channel.id
                            index += 1
                        
                        role = member.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID"))) 
                        await message.edit(content="", embed=queue_embed)

                        if len(self.matches[after.channel.id]["users"]) == self.matches[after.channel.id]["max"]:
                            self.matches[after.channel.id]["timestamp"] = int(time() + 30)

                            accept_embed = discord.Embed(color=0x248046, title=f"The queue has filled up! Expires <t:{self.matches[after.channel.id]["timestamp"]}:R>", description=f"Users accepted: 0/{self.matches[after.channel.id]["max"]}\n")
                            accept_embed.set_footer(text="Click on button to accept, you have 30 seconds!")

                            accept_view = self.AcceptView(self, timeout=30)  
                            asyncio.create_task(accept_view.start_timer())

                            accept_content = ""
                            for user in self.matches[after.channel.id]["users"]:
                                accept_content += f"<@{user}> "
                            
                            await after.channel.set_permissions(role, connect=False)

                            accept_message = await message.channel.send(content=accept_content, embed=accept_embed, view=accept_view)
                            await message.delete()

                            self.matches[after.channel.id]["state"] = "accept"
                            self.matches[after.channel.id]["message"] = accept_message.id

                        await after.channel.set_permissions(role, connect=False)
                        asyncio.create_task(self.revert_permissions(after.channel, role))

            else:
                if before.channel and before.channel.id in self.matches:
                    if len(self.matches[before.channel.id]["users"]) > 0 and member.id in self.matches[before.channel.id]["users"] and self.matches[before.channel.id]["state"] == "search":
                        self.matches[before.channel.id]["users"].pop(member.id)
                        
                        for group in self.matches[before.channel.id]["groups"]:
                            if member.id in self.matches[before.channel.id]["groups"][group]:
                                self.matches[before.channel.id]["groups"][group].remove(member.id)
                         
                        role = member.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID")))

                        await before.channel.set_permissions(role, connect=False)
                        asyncio.create_task(self.revert_permissions(before.channel, role))
                       
                        message = await member.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(self.matches[before.channel.id]["message"])
                        
                        queue_embed = discord.Embed(color=0x5865F2, description="")
                        queue_embed.title = f'In queue: {len(self.matches[before.channel.id]["users"])}/{self.matches[before.channel.id]["max"]}'
                        queue_embed.set_footer(text="The search channel will be locked when it reaches max size.")
                        
                        index = 1
                        for user in self.matches[before.channel.id]["users"]:
                            queue_embed.description += f"{index}. {self.matches[before.channel.id]["users"][user]["name"]}\n"
                            index += 1

                        await message.edit(content="", embed=queue_embed)

    def get_max_party_size(self, matchid, max_players, current_players, parties):
        max_party_size = max_players // 2
        remaining_spots = max_players - len(current_players)

        if len(parties) == 0:
            return min(max_party_size, remaining_spots)
        
        largest_party_size = max(len(self.matches[matchid]["groups"][party]) for party in parties)
        return min(max_party_size, remaining_spots, largest_party_size)

    class GroupAcceptView(discord.ui.View):
        def __init__(self, matchmaking):
            super().__init__(timeout=15)

            self.matchmaking = matchmaking
            self.message = None
        
        @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
        async def accept_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            requests_to_delete = []

            for leader in self.matchmaking.awaiting_accept:
                if interaction.user and interaction.user.id == self.matchmaking.awaiting_accept[leader]:
                    leader_user = await self.matchmaking.bot.get_guild(int(os.getenv("GUILD_ID"))).query_members(user_ids=[leader])

                    if leader_user[0].voice and interaction.user.voice and leader_user[0].voice.channel.id == interaction.user.voice.channel.id:
                        match = self.matchmaking.matches[leader_user[0].voice.channel.id]

                        for group_leader, group_members in match["groups"].items():
                            if interaction.user.id in group_members:
                                error_embed = discord.Embed(title="Party", description=f"<@{interaction.user.id}>, you are already in a party!", color=0xDA373C)
                                error_embed.set_footer(text="You can leave your party by using /party leave")

                                await interaction.response.send_message(embed=error_embed)
                                return

                            if len(match["groups"][leader]) - 1 < self.matchmaking.get_max_party_size(leader_user[0].voice.channel.id, match["max"], match["users"], match["groups"]) + 1:
                                if interaction.user.id not in self.matchmaking.matches[leader_user[0].voice.channel.id]["users"]:
                                    error_embed = discord.Embed(title="Party", description=f"Could not join, you are not in the queue.", color=0xDA373C)
                                    error_embed.set_footer(text="Rejoin the voice channel and try again.")

                                    await interaction.response.send_message(embed=error_embed)
                                    return
                                 
                                self.matchmaking.matches[leader_user[0].voice.channel.id]["groups"][leader].append(interaction.user.id)

                                group = self.matchmaking.matches[leader_user[0].voice.channel.id]["groups"][leader]
                                unique_group = list(set(group))
                                self.matchmaking.matches[leader_user[0].voice.channel.id]["groups"][leader] = unique_group

                                requests_to_delete.append(leader)
                                
                                success_embed = discord.Embed(title="Party", description=f"<@{interaction.user.id}> joined <@{leader_user[0].id}> party.", color=0x248046)
                                success_embed.set_footer(text="You can leave the party by using /party leave.")

                                await interaction.response.send_message(embed=success_embed)
                            else:
                                requests_to_delete.append(leader)
                                error_embed = discord.Embed(title="Party", description=f"Could not join, <@{leader_user[0].id}> party reached max size.", color=0xDA373C)
                                await interaction.response.send_message(embed=error_embed)

            for request in requests_to_delete:
                self.matchmaking.awaiting_accept.pop(request)
    
    async def delete_request(self, request_id):
        await asyncio.sleep(15.0)

        if request_id in self.awaiting_accept:
            self.awaiting_accept.pop(request_id)
    
    @commands.hybrid_group(name="party", description="List users in your party or invite an user.", with_app_command=True)
    async def party_group(self, ctx, member: discord.Member = None):
        if member == None:
            if ctx.author.voice and ctx.author.voice.channel != None:
                if ctx.author.voice.channel.id in self.matches.keys():
                    content = ""
                   
                    for group_leader, group_members in self.matches[ctx.author.voice.channel.id]["groups"].items():
                        if ctx.author.id in group_members:
                            index = 1
                            for group_member in group_members:
                                if group_member in self.matches[ctx.author.voice.channel.id]["users"]:
                                    content += f"{index}. {self.matches[ctx.author.voice.channel.id]["users"][group_member]["name"]}\n"
                                    index += 1
                        
                    if content != "":
                        status_embed = discord.Embed(title="Party", description=content, color=0x5865F2)
                        status_embed.set_footer(text="Party members are guaranteed to play with each other in a team.")

                        await ctx.send(embed=status_embed)
                    else:
                        error_embed = discord.Embed(title="Party", description="You are not in a party.", color=0xDA373C)
                        error_embed.set_footer(text="To create a party, invite another user.")

                        await ctx.send(embed=error_embed)
        else:
            if ctx.author.voice and ctx.author.voice.channel != None:
                if member.voice and member.voice.channel.id == ctx.author.voice.channel.id:
                    if ctx.author.id != member.id:
                        if ctx.author.voice.channel.id in self.matches.keys():
                            for request_leader, request_user in self.awaiting_accept.items():
                                if request_user == member.id:
                                    error_embed = discord.Embed(title="Party", description=f"<@{member.id}> already has an awaiting request.", color=0xDA373C)
                                    error_embed.set_footer(text="If you don't want to accept the request, wait until it expires.")

                                    await ctx.send(embed=error_embed)
                                    return

                            member_already_in_group = False                            
                            for group_leader, group_members in self.matches[ctx.author.voice.channel.id]["groups"].items():
                                if member.id in group_members:
                                    member_already_in_group = True
                            
                            if member_already_in_group != True:
                                for group_leader, group_members in self.matches[ctx.author.voice.channel.id]["groups"].items():
                                    if ctx.author.id in group_members and ctx.author.id != group_leader:
                                        error_embed = discord.Embed(title="Party", description="You are not the leader of your party.", color=0xDA373C)
                                        error_embed.set_footer(text="You can leave your party by using /party leave.")

                                        await ctx.send(embed=error_embed)
                                        return

                                if ctx.author.id not in self.matches[ctx.author.voice.channel.id]["groups"]:
                                    self.matches[ctx.author.voice.channel.id]["groups"][ctx.author.id] = [ctx.author.id]
                                
                                if len(self.matches[ctx.author.voice.channel.id]["groups"][ctx.author.id]) - 1 < self.get_max_party_size(ctx.author.voice.channel.id, self.matches[ctx.author.voice.channel.id]["max"], self.matches[ctx.author.voice.channel.id]["users"], self.matches[ctx.author.voice.channel.id]["groups"]) + 1:
                               
                                    if ctx.author.id not in self.matches[ctx.author.voice.channel.id]["users"]:
                                        error_embed = discord.Embed(title="Party", description="You are not in the queue.", color=0xDA373C)
                                        error_embed.set_footer(text="Rejoin the voice channel and try again.")

                                        await ctx.send(embed=error_embed)
                                        return

                                    self.awaiting_accept[ctx.author.id] = member.id
                                    asyncio.create_task(self.delete_request(ctx.author.id))

                                    group_accept_view = self.GroupAcceptView(self)
                                    
                                    invite_embed = discord.Embed(title="Party", description=f"<@{member.id}> you have been invited to <@{ctx.author.id}> party! Expires <t:{int(time() + 15)}:R>", color=0x248046)
                                    invite_embed.set_footer(text="Click on button to accept, you have 15 seconds!")

                                    await ctx.send(embed=invite_embed, view=group_accept_view)
                                else:
                                    if len(self.matches[ctx.author.voice.channel.id]["groups"][ctx.author.id]) == 1:
                                        self.matches[ctx.author.voice.channel.id]["groups"].pop(ctx.author.id)
                                    
                                    error_embed = discord.Embed(title="Party", description=f"<@{ctx.author.id}> your party has reached max size!", color=0xDA373C)
                                    error_embed.set_footer(text="You can kick someone from your party by using /party kick @user.")

                                    await ctx.send(embed=error_embed)
                            else:
                                error_embed = discord.Embed(title="Party", description=f"<@{member.id}> is already in a party.", color=0xDA373C)
                                error_embed.set_footer(text="You can leave your party by using /party leave.")

                                await ctx.send(embed=error_embed)
                else:
                    error_embed = discord.Embed(title="Party", description="You need to be in the same voice channel.", color=0xDA373C)
                    error_embed.set_footer(text="Join the same voice channel and try again.")

                    await ctx.send(embed=error_embed)

    @party_group.command(name="remove", aliases=["kick"], description="Removes user from your party.")
    async def remove(self, ctx, member: discord.Member):
        if ctx.author.voice and ctx.author.voice.channel != None:
            if ctx.author.id != member.id:
                if ctx.author.voice.channel.id in self.matches.keys():
                    for group_leader, group_members in self.matches[ctx.author.voice.channel.id]["groups"].items():
                        if ctx.author.id == group_leader:
                            if member.id in self.matches[ctx.author.voice.channel.id]["groups"][ctx.author.id]:
                                self.matches[ctx.author.voice.channel.id]["groups"][ctx.author.id].remove(member.id)
                                
                                if len(self.matches[ctx.author.voice.channel.id]["groups"][ctx.author.id]) == 1:
                                    self.matches[ctx.author.voice.channel.id]["groups"].pop(ctx.author.id)

                                success_embed = discord.Embed(title="Party", description=f"<@{member.id}> was successfully removed from your party.", color=0x248046)
                                await ctx.send(embed=success_embed)
                                
                                return
                            else:
                                error_embed = discord.Embed(title="Party", description=f"<@{member.id}> is not in your party!", color=0xDA373C)
                                error_embed.set_footer(text="You can invite users by using /party @user")

                                await ctx.send(embed=error_embed)
                                return

                    error_embed = discord.Embed(title="Party", description=f"You are not in a party or are not the leader!", color=0xDA373C)
                    error_embed.set_footer(text="To create a party, invite another user.")

                    await ctx.send(embed=error_embed)

    @party_group.command(name="quit", aliases=["leave"], description="Leaves your party.")
    async def quit(self, ctx):
        if ctx.author.voice and ctx.author.voice.channel != None:
            if ctx.author.voice.channel.id in self.matches.keys():
                for group_leader, group_members in self.matches[ctx.author.voice.channel.id]["groups"].items():
                    if ctx.author.id in group_members:
                        self.matches[ctx.author.voice.channel.id]["groups"][group_leader].remove(ctx.author.id)

                        if ctx.author.id == group_leader:
                            self.matches[ctx.author.voice.channel.id]["groups"].pop(group_leader)
                        elif len(self.matches[ctx.author.voice.channel.id]["groups"][group_leader]) == 1:
                            self.matches[ctx.author.voice.channel.id]["groups"].pop(group_leader)

                        success_embed = discord.Embed(title="Party", description="You successfully left the party.", color=0x248046)
                        success_embed.set_footer(text="You can create a party by using /party @user.")

                        await ctx.send(embed=success_embed) 

                error_embed = discord.Embed(title="Party", description="You are not in a party.", color=0xDA373C)
                error_embed.set_footer(text="To create a party, invite another user")

                await ctx.send(embed=error_embed)

    @commands.hybrid_command(name="reset", description="Reset matchmaking state.")
    @commands.has_permissions(administrator=True)
    async def reset(self, ctx, id):
        if ctx.guild and ctx.guild.id == int(os.getenv("GUILD_ID")) and ctx.author.guild_permissions.administrator:
            if id and int(id) in self.matches:
                self.matches[int(id)] = {
                    "max": self.matches[int(id)]["max"],
                    "region": self.matches[int(id)]["region"],
                    "map": "de_cache",
                    "users": {},
                    "groups": {},
                    "state": "pre-search",
                    "message": None,
                    "id": None,
                    "timestamp": 0,
                }
                
                success_embed = discord.Embed(title="Success", description="Successfully reseted queue state.", color=0x248046)
                await ctx.send(embed=success_embed)
            else:
                error_embed = discord.Embed(title="Error", description="Could not find queue. Is channel id correct?", color=0xDA373C)
                await ctx.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Matchmaking(bot))
