# IMPORTS
from os import getcwd
from sys import exc_info
from typing import List
from asyncio.exceptions import TimeoutError

from discord import Embed as DiscordEmbed
from expiringdict import ExpiringDict
from discord.ext.commands import (
    Bot as DiscordBot)

from utils.utils import fetch_array_item, ZWSP
from utils.map_data import MAIN_MAP

# Override default color for bot fanciness
class Embed(DiscordEmbed):
    def __init__(self, *args, **kwargs):
        color = kwargs.pop("color", 0x000000)
        if not color:
            color = 0x70eaff
        
        super().__init__(*args, color=color, **kwargs)

class Paginator:
    def __init__(
            self,
            page_limit: int = 1000,
            trunc_limit: int = 2000,
            headers: List[str] = None,
            header_extender: str = u'\u200b'
    ):
        self.page_limit = page_limit
        self.trunc_limit = trunc_limit
        self._pages = None
        self._headers = None
        self._header_extender = header_extender
        self.set_headers(headers)

    @property
    def pages(self):
        if self._headers:
            self._extend_headers(len(self._pages))
            headers, self._headers = self._headers, None
            return [
                (headers[i], self._pages[i]) for i in range(len(self._pages))
            ]
        else:
            return self._pages

    def set_headers(self, headers: List[str] = None):
        self._headers = headers

    def set_header_extender(self, header_extender: str = u'\u200b'):
        self._header_extender = header_extender

    def _extend_headers(self, length: int):
        while len(self._headers) < length:
            self._headers.append(self._header_extender)

    def set_trunc_limit(self, limit: int = 2000):
        self.trunc_limit = limit

    def set_page_limit(self, limit: int = 1000):
        self.page_limit = limit

    def paginate(self, value):
        """
        To paginate a string into a list of strings under
        `self.page_limit` characters. Total len of strings
        will not exceed `self.trunc_limit`.
        :param value: string to paginate
        :return list: list of strings under 'page_limit' chars
        """
        spl = str(value).split('\n')
        ret = []
        page = ''
        total = 0
        for i in spl:
            if total + len(page) < self.trunc_limit:
                if (len(page) + len(i)) < self.page_limit:
                    page += '\n{}'.format(i)
                else:
                    if page:
                        total += len(page)
                        ret.append(page)
                    if len(i) > (self.page_limit - 1):
                        tmp = i
                        while len(tmp) > (self.page_limit - 1):
                            if total + len(tmp) < self.trunc_limit:
                                total += len(tmp[:self.page_limit])
                                ret.append(tmp[:self.page_limit])
                                tmp = tmp[self.page_limit:]
                            else:
                                ret.append(tmp[:self.trunc_limit - total])
                                break
                        else:
                            page = tmp
                    else:
                        page = i
            else:
                ret.append(page[:self.trunc_limit - total])
                break
        else:
            ret.append(page)
        self._pages = ret
        return self.pages

class BotInteractionCooldown(Exception):
    pass

class Bot(DiscordBot):

    def __init__(self, *args, **kwargs):
        # Timer to track minutes since responded to a command.
        self.inactive = 0

        # Global bot directory
        self.cwd = getcwd()

        # Change first half of text status
        self.text_status = f"{kwargs.get('command_prefix')}help"

        # Tokens
        self.auth = kwargs.pop("auth")

        # Default data. Used to initialize and update data structures.
        self.defaults = kwargs.pop("defaults")
        
        # Database
        self.database = kwargs.pop("database")  # Online
        self.user_data = kwargs.pop("user_data") # Local
        self.config = self.user_data["config"]  # Shortcut for user_data['config']
        print("[] Data and configurations loaded.")

        # Get the channel ready for errorlog
        # Bot.get_channel method not available until on_ready
        self.errorlog_channel: int = kwargs.pop("errorlog", None)

        # Cooldown to be used in all loops and the beginnings of commands.
        # Users whose ID is in here cannot interact with the bot for `max_age_seconds`
        self.global_cooldown = ExpiringDict(max_len=float('inf'), max_age_seconds=2)

        # Users whose ID is in here cannot create another PDA until the one they are using expires.
        self.pda_active = dict()
        
        # Load bot arguments into __init__
        super().__init__(*args, **kwargs)
    
    def run(self, *args, **kwargs):
        print("[BOT INIT] Logging in with token...")
        super().run(self.auth["BOT_TOKEN"], *args, **kwargs)
    
    async def on_error(self, event_name, *args, **kwargs):
        '''Error handler for Exceptions raised in events'''
        if self.config["debug_mode"]:  # Hold true the purpose for the debug_mode option
            await super().on_error(event_method=event_name, *args, **kwargs)
            return
        
        # Try to get Exception that was raised
        error = exc_info()  # `from sys import exc_info` at the top of your script

        # If the Exception raised is successfully captured, use ErrorLog
        if error:
            await self.errorlog.send(error, event=event_name)

        # Otherwise, use default handler
        else:
            await super().on_error(event_method=event_name, *args, **kwargs)
    
    async def on_message(self, msg):
        """Disable primary Bot.process_commands listener for cogs to call individually."""
        return

    async def wait_for(self, *args, **kwargs):
        """Delay primary Bot.wait_for listener. Raises CommandOnCooldown if on cooldown."""
        bypass_cooldown: bool = kwargs.pop("bypass_cooldown", False)
        if bypass_cooldown:
            return await super().wait_for(*args, **kwargs)
        
        if "message" in args:
            msg = await super().wait_for(*args, **kwargs)
            if msg.author.id in self.global_cooldown: raise BotInteractionCooldown("Bot interaction on cooldown.")
            else: self.global_cooldown.update({msg.author.id:"placeholder"})
            return msg

        elif "reaction_add" in args:
            reaction, user = await super().wait_for(*args, **kwargs)
            if user.id in self.global_cooldown: raise BotInteractionCooldown("Bot interaction on cooldown.")
            else: self.global_cooldown.update({user.id:"placeholder"})
            return reaction, user
        
        else:
            return await super().wait_for(*args, **kwargs)

class PDA:
    def __init__(self, bot, ctx):
        self.bot = bot
        self.ctx = ctx
        self.data = bot.user_data["UserData"][str(ctx.author.id)]

        # Will be a new channel for the PDA
        self.am_channel = None

        # Four messages are created for the PDA channel.
        # 0] User Interface
        # 1] Reaction controller row 1: arrow_upper_left | arrow_up    | arrow_upper_right
        # 2] Reaction controller row 2: arrow_left       | blue_square | arrow_right
        # 3] Reaction controller row 3: arrow_lower_left | arrow_down  | arrow_lower_right
        self.active_messages = [None, None, None, None, None]

        # Embed for the User Interface active message.
        self.am_embed = None
        self.current_page = 0
        self.in_subpage = False

    async def setup(self):
        self.am_channel = await self.ctx.guild.create_text_channel("📱asterisk-pda")
        self.active_messages[0] = await self.am_channel.send(
            embed=Embed(description="Waiting for PDA to start..."))
        
        self.active_messages[1] = await self.am_channel.send(ZWSP)
        await self.active_messages[1].add_reaction("↖")
        await self.active_messages[1].add_reaction("⬆")
        await self.active_messages[1].add_reaction("↗")
        self.active_messages[2] = await self.am_channel.send(ZWSP)
        await self.active_messages[2].add_reaction("⬅")
        await self.active_messages[2].add_reaction("🔎")
        await self.active_messages[2].add_reaction("➡")
        self.active_messages[3] = await self.am_channel.send(ZWSP)
        await self.active_messages[3].add_reaction("↙")
        await self.active_messages[3].add_reaction("⬇")
        await self.active_messages[3].add_reaction("↘")
        self.active_messages[4] = await self.am_channel.send(ZWSP)
        await self.active_messages[4].add_reaction("❎")
        await self.active_messages[4].add_reaction("❌")
        await self.active_messages[4].add_reaction("✅")
    
    async def start(self):
        coordinates = f"{self.data['Location'][0][0]}-{self.data['Location'][0][1]}={self.data['Location'][1][0]}-{self.data['Location'][1][1]}"
        sector = fetch_array_item(MAIN_MAP, self.data['Location'][0][0], 
        self.data['Location'][0][1])['Name']
        area = fetch_array_item(fetch_array_item(MAIN_MAP, self.data['Location'][0][0], self.data['Location'][0][1])['Map'], 
            self.data['Location'][1][0], self.data['Location'][1][1])["Name"]

        location = Embed(
            title="Map"
        ).add_field(
                name="Current Sector",
                value=f"{sector} | {coordinates}"
        ).add_field(
            name="Current Area",
            value=f"{area}")

        await self.active_messages[0].edit(embed=location)
        
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=300,
                    check=lambda r,u: r.message.id in [m.id for m in self.active_messages] and \
                        u.id==self.ctx.author.id)
            except TimeoutError:
                await self.am_channel.delete()
                return
            
            except BotInteractionCooldown:
                continue
            
            else:
                await reaction.message.remove_reaction(str(reaction.emoji), user)

                if not self.in_subpage:
                    # Location data
                    coordinates = f"{self.data['Location'][0][1]}-{self.data['Location'][0][0]}={self.data['Location'][1][0]}-{self.data['Location'][1][1]}"
                    sector = fetch_array_item(MAIN_MAP, self.data['Location'][0][0], 
                    self.data['Location'][0][1])['Name']
                    area = fetch_array_item(fetch_array_item(MAIN_MAP, self.data['Location'][0][0], self.data['Location'][0][1])['Map'], 
                        self.data['Location'][1][0], self.data['Location'][1][1])["Name"]

                    menus = [
                        {"Name": "Map",
                         "Embed": Embed(title="Map")
                            .add_field(
                                name="Current Sector",
                                value=f"{sector} | {coordinates}")
                            .add_field(
                                name="Current Area",
                                value=f"{area}")
                            .add_field(
                                inline=False,
                                name="Description")
                        },
                        {"Name": "Inventory",
                         "Embed": Embed()},
                        {"Name": "Armor and Stats",
                         "Embed": Embed()},
                        {"Name": "Friends",
                         "Embed": Embed()}
                    ]

                await self.active_messages[0].edit(embed=menus[self.current_page]["Embed"])

