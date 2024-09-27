import os
import json
import logging
import asyncio

from collections import Counter
from datetime import timedelta

import discord
from discord.ext import commands

from valve.rcon import RCON, RCONError

class Matchmaking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.matches = {
                1281757327204159501: {
                    "max": 2,
                    "map": "de_cache",
                    "users": {}, 
                    "groups": {},
                    "state": "pre-search", 
                    "message": None,
                    "id": None
                }
        }

        self.awaiting_accept = {}
    
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
                    await message.edit(content=None, embed=map_embed, view=map_view)

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
                        if match["users"][user]["accepted"] == False:
                            not_accepted.append(user)
                        else:
                            match["users"][user]["accepted"] = False

                    for user in not_accepted:
                        match["users"].pop(user)

                        member = await self.matchmaking.bot.get_guild(int(os.getenv("GUILD_ID"))).query_members(user_ids=[user]) 
                        await member[0].move_to(channel=None)

                        if not member[0].guild_permissions.administrator:
                            await member[0].timeout(timedelta(minutes=3))

                    queue_embed = discord.Embed(color=0x808080, title=f'In queue: {len(match["users"])}/{match["max"]}', description="")
                    
                    index = 1
                    for user in match["users"]:
                        queue_embed.description += f"{index}. {match["users"][user]["name"]}\n"
                        index += 1
                    
                    key = list(match.keys())
                    channel = self.matchmaking.bot.get_channel(key[0])
                    role = self.matchmaking.bot.get_guild(int(os.getenv("GUILD_ID"))).get_role(int(os.getenv("VERIFIED_ROLE_ID")))

                    asyncio.create_task(self.matchmaking.revert_permissions(channel, role))
                    
                    channel = self.matchmaking.bot.get_channel(int(os.getenv("QUEUE_CHANNEL_ID")))

                    message = await channel.fetch_message(match["message"]) 
                    await message.delete()

                    queue_msg = await channel.send(embed=queue_embed) 
                    match["message"] = queue_msg.id

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

            for match_id, match_data in self.matchmaking.matches.items():
                if match_data["message"] == interaction.message.id and match_data["state"] == "map":
                    match = match_data

            if match and interaction.user.id in match["users"]:
                match["users"][interaction.user.id]["vote"] = selected_map
                await interaction.response.send_message(f"Your choice: {selected_map}", ephemeral=True)

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
            match = None

            for match_id, match_data in self.matchmaking.matches.items():
                if match_data["state"] == "map":
                    match = match_data

            if match:
                ready_embed = discord.Embed(color=0x808080, title="Preparing server...", description="*This can take up to 2-3 minutes*")

                message = await self.matchmaking.bot.get_guild(int(os.getenv("GUILD_ID"))).get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(match["message"]) 
                await message.edit(embed=ready_embed, view=None)
 
                votes = [user["vote"] for user in match["users"].values()] 
                vote_count = Counter(votes)
                max_votes = max(vote_count.values())

                maps = [map for map, count in vote_count.items() if count == max_votes]

                if maps[0] != None:
                    match["map"] = maps[0]

                await self.matchmaking.prepare_server(match)

    async def prepare_server(self, match):
        match["state"] = "preparing"
                    
        with self.bot.database.cursor() as cursor:
            team_ct = []
            team_t = []
            
            players = {}
            
            half = len(match["users"]) // 2
            index = 0

            for id, user in list(match["users"].items())[:half]:
                query = "SELECT steam64 FROM Players WHERE idDiscord = %s"

                cursor.execute(query, (str(id),))
                row = cursor.fetchone()

                team_ct.append(id)
                
                if row:
                    players[index] = int(row[0])
                    match["users"][id]["steamid"] = row[0]

                index += 1

            for id, user in list(match["users"].items())[half:]:
                query = "SELECT steam64 FROM Players WHERE idDiscord = %s"

                cursor.execute(query, (str(id),))
                row = cursor.fetchone()

                team_t.append(id)
                
                if row:
                    players[index] = int(row[0])
                    match["users"][id]["steamid"] = row[0]
                
                index += 1

            ports = os.getenv("SERVER_PORTS").split(",");
            server_port = 0

            for port in ports:
                await asyncio.sleep(1.5)
            
                try: 
                    with RCON((os.getenv("SERVER_IP"), int(port)), os.getenv("RCON_PASS")) as rcon:
                        result = rcon(f'sm_setupmatch {match["map"]} "team_{match["users"][team_ct[0]]["name"]}" "team_{match["users"][team_t[0]]["name"]}"')
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
        
            if server_port == 0:
                embed_error = discord.Embed(title="**Error**", description="Couldnt find any available servers. Please wait or contact an administrator.", color=0x808080)
            
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

                max_players = match["max"]
                self.matches[match["id"]] = {
                    "max": max_players,
                    "map": "de_cache",
                    "users": {}, 
                    "groups": {},
                    "state": "pre-search", 
                    "message": None,
                    "id": None,
                }
            
                return

            ip = str(os.getenv("SERVER_IP")) + ":" + str(server_port)

            query = "INSERT INTO whitelist (ip, players) VALUES (%s, %s)"
            cursor.execute(query, (ip, json.dumps(players)))

        await asyncio.sleep(60.0)

        embed_ready = discord.Embed(title=f'**The server is ready! team_{match["users"][team_ct[0]]["name"]} VS team_{match["users"][team_t[0]]["name"]}**', description="The server is Ready! GLHF!", color = 0x808080)
        
        embed_ready.add_field(name="**IP**", value=f'``{str(os.getenv("SERVER_IP"))}:{str(server_port)}``', inline=True)

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
        
        message = await self.bot.get_guild(int(os.getenv("GUILD_ID"))).get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(match["message"]) 
        await message.edit(embed=embed_ready, view=None)
        
        channel = self.bot.get_channel(match["id"])
        role = self.bot.get_guild(int(os.getenv("GUILD_ID"))).get_role(int(os.getenv("VERIFIED_ROLE_ID")))

        asyncio.create_task(self.revert_permissions(channel, role))

        max_players = match["max"]
        self.matches[match["id"]] = {
            "max": max_players,
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
                queue_embed = discord.Embed(color=0x808080, title=f"In queue: 0/{self.matches[after.channel.id]["max"]}", description="")

                if self.matches[after.channel.id]["state"] == "pre-search":
                    queue_msg = await member.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).send(embed=queue_embed)

                    self.matches[after.channel.id]["message"] = queue_msg.id
                    self.matches[after.channel.id]["state"] = "search"

                if after.channel and member.id not in self.matches[after.channel.id]["users"]: 
                    if len(self.matches[after.channel.id]["users"]) < self.matches[after.channel.id]["max"] and self.matches[after.channel.id]["state"] == "search": 
                        self.matches[after.channel.id]["users"][member.id] = { "name": member.name, "team": None, "steamid": None, "accepted": False, "vote": None }

                        message = await member.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(self.matches[after.channel.id]["message"])
                        
                        queue_embed.title = f'{member.name} joined. In queue: {len(self.matches[after.channel.id]["users"])}/{self.matches[after.channel.id]["max"]}'
                        
                        index = 1
                        for user in self.matches[after.channel.id]["users"]:
                            queue_embed.description += f"{index}. {self.matches[after.channel.id]["users"][user]["name"]}\n"

                            self.matches[after.channel.id]["id"] = after.channel.id
                            index += 1
                        
                        role = member.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID"))) 
                        await message.edit(embed=queue_embed)

                        if len(self.matches[after.channel.id]["users"]) == self.matches[after.channel.id]["max"]:
                            accept_embed = discord.Embed(color=0x808080, title="The queue has filled up!", description="*Click on button to accept, you have 30 seconds!*")
                            accept_view = self.AcceptView(self) 
                            
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
                         
                        role = member.guild.get_role(int(os.getenv("VERIFIED_ROLE_ID")))

                        await before.channel.set_permissions(role, connect=False)
                        asyncio.create_task(self.revert_permissions(before.channel, role))
                       
                        message = await member.guild.get_channel(int(os.getenv("QUEUE_CHANNEL_ID"))).fetch_message(self.matches[before.channel.id]["message"])
                        
                        queue_embed = discord.Embed(color=0x808080, description="")
                        queue_embed.title = f'{member.name} left. In queue: {len(self.matches[before.channel.id]["users"])}/{self.matches[before.channel.id]["max"]}'
                        
                        index = 1
                        for user in self.matches[before.channel.id]["users"]:
                            queue_embed.description += f"{index}. {self.matches[before.channel.id]["users"][user]["name"]}\n"
                            index += 1

                        await message.edit(embed=queue_embed)

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
                        self.matchmaking.matches[leader_user[0].voice.channel.id]["groups"][leader].append(interaction.user.id)
                        requests_to_delete.append(leader)

                        await interaction.response.send_message(f"{interaction.user.name} accepted {leader_user[0].name} invite.")

            for request in requests_to_delete:
                self.matchmaking.awaiting_accept.pop(request)
    
    async def delete_request(self, request_id):
        await asyncio.sleep(15.0)

        if request_id in self.awaiting_accept:
            self.awaiting_accept.pop(request_id)

    @commands.hybrid_command(name="group", description="Add an user to your group.")
    async def group(self, ctx, member: discord.Member):
        if ctx.author.voice and ctx.author.voice.channel != None:
            if member.voice and member.voice.channel.id == ctx.author.voice.channel.id:
                if ctx.author.id != member.id:
                    if ctx.author.voice.channel.id in self.matches.keys():
                        member_already_in_group = False

                        for group_leader, group_members in self.matches[ctx.author.voice.channel.id]["groups"].items():
                            if member.id in group_members:
                                member_already_in_group = True
                        
                        if member_already_in_group != True:
                            if ctx.author.id not in self.matches[ctx.author.voice.channel.id]["groups"]:
                                self.matches[ctx.author.voice.channel.id]["groups"][ctx.author.id] = [ctx.author.id]
                            
                            self.awaiting_accept[ctx.author.id] = member.id
                            asyncio.create_task(self.delete_request(ctx.author.id))

                            group_accept_view = self.GroupAcceptView(self)

                            await ctx.send(content=f"<@{member.id}> you have been invited to group by {ctx.author.name}! Click on button to accept.", view=group_accept_view)
                        else:
                            await ctx.send(content=f"{member.name} is already in a group!")
            else:
                await ctx.send("You need to be in the same voice channel!")

async def setup(bot):
    await bot.add_cog(Matchmaking(bot))
