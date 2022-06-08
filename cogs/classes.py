# IMPORTS
from dataclasses import dataclass
from sys import exc_info
from copy import deepcopy
from textwrap import shorten
from asyncio import sleep
from asyncio.exceptions import TimeoutError
from contextlib import suppress
from turtle import rt
from typing import List, Union
from json import dump, load

from discord import (
    Message, TextChannel,
    Forbidden, NotFound)
from discord.utils import get
from discord.ext.tasks import loop
from discord.ext.commands import Context
from discord.ext.commands.cog import Cog

from utils.classes import Embed, Bot, BotInteractionCooldown

newline = "\n"

class Classes(Cog):
    def __init__(self, bot):
        self.bot = bot

## Basic item stats
# name: str
# The name is customizable and doesn't affect custom-built items.
#
# faction: str 
# Seidoukan Academy, Arlequint Academy, Jie Long Seventh Institute, 
# Rewolf Black Institute, Saint Galahadworth Academy, Queenvail Girls' Academy
# Homemade (no faction, typically for Flawed and some Cheap things)
# 
# rarity: str
# Flawed, Cheap, Rare, Elite, Exotic, Custom-built
# Exotics can have special effects, while Custom-builts can have special affects and special attacks.
#
# level: int
# This level also reflects the level the user is required to be to equip it.

class ArmorItem:
    def __init__(self, **armor_values):
        self.name: str = armor_values.pop("name")
        self.faction: str = armor_values.pop("faction")
        self.rarity: str = armor_values.pop("rarity")
        self.level: int = armor_values.pop("level")

        # Used in an equation to subtract incoming damage.
        self.defense = armor_values.pop("defense", 2)


class WeaponItem:
    def __init__(self, **weapon_values):
        self.name: str = weapon_values.pop("name", "Hand-me-down Dagger")
        self.faction: str = weapon_values.pop("faction", "Homemade")
        self.rarity: str = weapon_values.pop("rarity", "Flawed")
        self.experience: int = weapon_values.pop("experience", 0)

        # The type of weapon, though mostly irrelavent. It can help with balance.
        # | Damage | Defense | Speed |
        # Distribute 6 stars. Negatives add stars for other categories.
        # 
        # Current types include:
        # Knife:       | ++    |      | ++++  |
        # Shortsword:  | ++    | +    | +++   |
        # Broadsword:  | +++   | ++   | +     |
        # Mace:        | ++++  |      | ++    |
        # Hammer:      | +++++ | ++   | -     |
        # Sickle:      | ++++  | +    | +     |
        self.weapon_type = weapon_values.pop("weapon_type", "Knife")

        # The base damage of the weapon.
        self.damage = weapon_values.pop("damage", 10)

        # If the quickdraw is more than the speed of the enemy player, the turn is not skipped when switching to it.
        self.quickdraw = weapon_values.pop("quickdraw", 10)

        # Adds to total defense, this applies when attacked while holding this weapon.
        self.defense = weapon_values.pop("defense", 1)


class InventoryItem:
    def __init__(self, *item_values):
        self.name: str = item_values.pop("name", "Dagger")
        self.faction: str = item_values.pop("faction", "Homemade")
        self.rarity: str = item_values.pop("rarity", "Flawed")
        self.experience: int = item_values.pop("experience", 0)

        # A basic reminder about the item
        self.tooltip = item_values.pop("tooltip")

    async def use1(player):
        pass


class Player:
    """ Convert all player json data into a data class for interactives """
    def __init__(self, **player_stats):
        self.name = player_stats.pop("Name")
        self.life = player_stats.pop("Life")[0]
        self.prana = player_stats.pop("Prana")[0]
        self.attack = player_stats.pop("Attack")
        self.insight = player_stats.pop("Insight")
        self.speed = player_stats.pop("Speed")

        self.weapons = []
        for weapon in player_stats.pop("Weapons"):
            self.weapons.append(WeaponItem(**weapon))
        
        self.armor = []
        for armor_piece in player_stats.pop("Armor"):
            self.armor.append(ArmorItem(**armor_piece))

class MultiplayerInstance:
    def __init__(self, init_client, instances: tuple, **game_settings):
        self.multiplayer_instances = instances[0]
        self.client_instances = instances[1]

        # The list of clients connected to this instance.
        self.host_client = init_client
        self.host_client.is_host_client = True
        self.clients = [].append(init_client)

        # The game mode the game will run on. Certain game modes have max player limits.
        # `duals` default to 2, `double-duel` defaults to 4, `co-op` defaults to 4.
        self.gamemode = game_settings.pop("mode", "duel")
        self.player_limit = game_settings.pop("limit", 2)
        self.is_invite_only = game_settings.pop("private", False)

        # For PVP games, time in seconds the game is allowed to last. The person/team with the highest health will win if it expires.
        self.time_limit = game_settings.pop("time", 300)

        self.incoming_packets = []  # recieve data from AsteriskClient
        self.outgoing_packets = []  # send data to AsteriskClient

    async def setup(self):
        self.multiplayer_instances.append(self)
        self.incoming_packet_handler.start()
        self.outgoing_packet_handler.start()

    async def destroyInstance(self):
        self.multiplayer_instances.remove(self)
        for client in self.clients:
            if not client.is_host_client:
                client.incoming_packets.append({
                    "from": 0,
                    "target": client._id,
                    "is_multiplayer": True, 
                    "type": "multiplayerGameDisbanded",
                    "value": None})

        del self

    @loop(seconds=0.2)
    async def incoming_packet_handler(self):
        if not self.incoming_packets:
            return

        packet = self.incoming_packets.pop(0)
        if "target" not in packet:
            print(f"[AST] MASTER WARNING: Incoming packet `{packet}` has no `target` parameter.")
            return
        if "from" not in packet:
            print(f"[AST] MASTER WARNING: Incoming packet `{packet}` has no `from` parameter.")
            return
        if "is_multiplayer" not in packet:
            print(f"[AST] MASTER WARNING: Incoming packet `{packet}` has no `is_multiplayer` parameter.")
            return

        target = get(self.client_instances, _id=packet["target"])
        if not target:
            print(f"[AST] MASTER WARNING: The target of packet `{packet}` does not exist.")
            return
        client = get(self.client_instances, _id=packet["from"])
        if not client:
            print(f"[AST] MASTER WARNING: The origin of packet `{packet}` is unknown.")
            return

        elif target == 0:  # Packet is for this instance to handle
            if not packet["is_multiplayer"]:
                print(f"[AST] MASTER WARNING: Recieved packet `{packet}` which was not meant for multiplayer!")
                return

            if packet["type"] == "joinRequest":
                # Expected value is the client that has joined or has asked to join.
                if self.is_invite_only:
                    self.host_client.incoming_packets.append({
                        "from": 0,
                        "target": packet["value"]._id, 
                        "is_multiplayer": False,
                        "type": "joinRequest", 
                        "value": packet["value"]})
                else:
                    self.clients.append(packet["value"])
                    packet["value"].incoming_packets.append({
                        "from": 0,
                        "target": packet["value"]._id, 
                        "is_multiplayer": False,
                        "type": "joinApproved", 
                        "value": self})

            elif packet["type"] == "joinApprove" and packet["from"] == self.host_client._id:
                # Expected value is the client that has joined via request.
                self.clients.append(packet["value"])
                packet["value"].incoming_packets.append({
                    "from": 0,
                    "target":packet["value"]._id, 
                    "is_multiplayer": False,
                    "type": "joinApproved", 
                    "value": self})

            elif packet["type"] == "playerLeft":
                # Expected value is the client that left.
                self.clients.remove(packet["value"])
                packet["value"].in_game = False
                packet["value"].pending_notifications.append(Embed(
                    title="Left session",
                    description="You successfully left the multiplayer session."
                ))

            elif packet["type"] == "destroyInstance":
                # Expected value is the client that requested this instance to be destroyed.
                if packet["value"].is_host_client:
                    await self.destroyInstance()
                    packet["value"].incoming_packets.append({
                        "from": 0,
                        "target": packet["value"]._id,
                        "is_multiplayer": True,
                        "type": "multiplayerDisbandedSuccess",
                        "value": None
                    })

            else:
                print(f"[AST] MASTER WARNING: The master instance does not know what do with packet `{packet}`!")
        else:
            target.incoming_packets.append(packet)

class AsteriskClient:
    def __init__(self, inter, instances, gamemode="quickPlay"):
        self.multiplayer_instances = instances[0]
        self.client_instances = instances[1]

        self._id = inter.message.id
        self.inter = inter

        self.multiplayer_instance: MultiplayerInstance = None
        self.searching = False
        self.target_gamemode = gamemode
        self.is_host_client = False
        self.join_requests = []

        self.pending_notifications = []
        self.in_game = False  # Notifications won't show while in_game=True
        self.player: Player = self.bot.user_data["UserData"][str(self.ctx.author.id)]["Character"]
        if self.player.name == "useDiscordName":
            self.player.name = str(self.inter.user)
        
        self.active_message = None
        self.am_embed = None
        self.am_channel = None

        self.incoming_packets = []  # recieve data from MultiplayerInstance
        self.outgoing_packets = []  # send data to MultiplayerInstance

    async def setup(self):
        self.client_instances.append(self)
        self.am_channel = await self.ctx.guild.create_text_channel("📱asterisk-client")
        self.am_embed = Embed(
            title="Asterisk",
            description="<a:loading:813237675553062954> Setting up..."
        )
        self.active_message.send(embed=self.am_embed)
        
        self.incoming_packet_handler.start()
        self.outgoing_packet_handler.start()
        self.incoming_notifications.start()

    @loop(seconds=1)
    async def main_loop(self):
        self.am_embed = Embed(
            title=self.player.name,
            description=f""
        )

    async def quit(self):
        self.client_instances.remove(self)
        self.incoming_notifications.stop()
        if self.multiplayer_instance:
            # skip the outgoing_packets_handler since it will be stopping very shortly
            self.multiplayer_instance.incoming_packets.append({
                "from": self._id,
                "target": 0,
                "is_multiplayer": True,
                "type": "playerLeft",
                "value": self
            })

        self.am_channel.delete()
        self.incoming_packet_handler.stop()
        self.outgoing_packet_handler.stop()
        del self

    @loop(seconds=1)
    async def incoming_notifications(self):
        if self.pending_notifications:
            self.am_channel.send(embed=self.pending_notifications.pop(0))

    @loop(seconds=0.2)
    async def incoming_packet_handler(self):
        if not self.incoming_packets:
            return

        packet = self.incoming_packets.pop(0)
        if "target" not in packet:
            print(f"[AST] CLIENT IN WARNING: Incoming packet `{packet}` has no `target` parameter.")
            return
        if "from" not in packet:
            print(f"[AST] CLIENT IN WARNING: Incoming packet `{packet}` has no `from` parameter.")
            return
        if "is_multiplayer" not in packet:
            print(f"[AST] CLIENT IN WARNING: Incoming packet `{packet}` has no `is_multiplayer` parameter.")
            return

        target = get(self.client_instances, _id=packet["target"])
        if not target:
            print(f"[AST] CLIENT IN WARNING: The target of packet `{packet}` does not exist.")
            return
        client = get(self.client_instances, _id=packet["from"])
        if not client:
            print(f"[AST] CLIENT IN WARNING: The origin of packet `{packet}` is unknown.")
            return

        if packet["target"] == self._id:
            if packet["is_multiplayer"]:
                if packet["type"] == "joinRequest" and self.is_host_client:
                    # Expected value is the client that requested to join the multplayer instance.
                    self.join_requests.append(packet["value"])

                elif packet["type"] == "joinApproved":
                    # Expected value is the instance that the client was approved to join.
                    self.multiplayer_instance = packet["value"]

                elif packet["type"] == "leftSuccess":
                    # No expected value
                    self.multiplayer_instance = None

                elif packet["type"] == "multiplayerGameDisbanded":
                    self.multiplayer_instance = None
                    self.pending_notifications.append(Embed(
                        title="Connection lost",
                        description="The multiplayer game host disbanded the session. You can search for another session or create your own."
                    ))
                elif packet["type"] == "multiplayerDisbandedSuccess":
                    self.pending_notifications.append(Embed(
                        title="Disband success",
                        description="The session is now disbanded. You can create a new one or search for another session."
                    ))

                else:
                    print(f"[AST] CLIENT IN WARNING: The client does not know what to do with packet `{packet}`!")
                
            else:
                if packet["type"] == "friendRequest":
                    # Expected value is the client that sent the request.
                    self.bot.user_data["UserData"][str(self.inter.user.id)]["Friend Requests"].append(packet["value"].inter.user.id)
                    self.pending_notifications.append(Embed(
                        title="👋 Friend request!",
                        description=f"New friend request from {packet['value'].player.name} (`{packet['value'].inter.user}`)"
                    ))
                else:
                    print(f"[AST] CLIENT IN WARNING: The client does not know what to do with packet `{packet}`!")

        else:
            # Theoretically, this should never be reached
            print(f"[AST] CLIENT WARNING: Client recieved packet '{packet}' which is marked for a different destination!")

    @loop(seconds=0.2)
    async def outgoing_packet_handler(self):
        if not self.outgoing_packets:
            return

        packet = self.outgoing_packets.pop(0)
        if "target" not in packet:
            print(f"[AST] CLIENT OUT WARNING: Outgoing packet `{packet}` has no `target` parameter.")
            return
        if "from" not in packet:
            print(f"[AST] CLIENT OUT WARNING: Outgoing packet `{packet}` has no `from` parameter.")
            return
        if "is_multiplayer" not in packet:
            print(f"[AST] CLIENT OUT WARNING: Outgoing packet `{packet}` has no `is_multiplayer` parameter.")
            return
        
        if packet["is_multiplayer"] and not self.multiplayer_instance:
            print(f"[AST] CLIENT OUT WARNING: Outgoing packet `{packet}` contains multiplayer information, but the client isn't connected!")
            return

        target = get(self.client_instances, _id=packet["target"])
        if not target:
            print(f"[AST] CLIENT OUT WARNING: The target of packet `{packet}` does not exist.")
            return
        client = get(self.client_instances, _id=packet["from"])
        if not client:
            print(f"[AST] CLIENT OUT WARNING: The origin of packet `{packet}` is unknown.")
            return

        if packet["target"] != self._id:
            if packet["is_multiplayer"]:
                if packet["type"] == "playerLeft":
                    target.incoming_packets.append({
                        "from": self._id,
                        "target": 0,
                        "is_multiplayer": True,
                        "type": "playerLeft",
                        "value": self
                    })
                else:
                    print(f"[AST] CLIENT OUT WARNING: The client does not know what to do with packet `{packet}`!")
            else:
                if packet["type"] == "friendRequest":
                    # Expected value is the client that sent the friend request.
                    target.incoming_packets.append({
                        "from": self._id,
                        "target": packet["value"]._id,
                        "is_multiplayer": False,
                        "type": "friendRequest",
                        "value": self
                    })

                else:
                    print(f"[AST] CLIENT OUT WARNING: The client does not know what to do with packet `{packet}`!")
                    


async def setup(bot):
    await bot.add_cog(Classes(bot))