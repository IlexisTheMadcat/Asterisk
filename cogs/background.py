from json import dump, dumps
from asyncio import sleep
from aiohttp import ClientSession
from datetime import datetime

from discordspy import Post as DiscordsPost, Client as DiscordsClient
from discord.activity import Activity
from discord.enums import ActivityType, Status
from discord.ext.commands.cog import Cog
from discord.ext.tasks import loop
from discord.errors import NotFound
from discord.ext.commands import is_owner
from discord.ext.commands.core import command
from timeit import default_timer

from utils.classes import Embed

class BackgroundTasks(Cog):
    """Background loops"""

    def __init__(self, bot):
        self.bot = bot
        self.save_data.start()
        self.status_change.start()

        # self.del_update_stats.start()
        # self.discords = DiscordsClient(bot, self.bot.auth["DISCORDS_TOKEN"])
        # self.discords_update_stats.start()

    @is_owner()
    @command()
    async def restart_task(self, ctx, task):
        try: task_object = getattr(self, task)
        except AttributeError: 
            return await ctx.send(
                embed=Embed(
                    color=0xff0000,
                    title="Task Not Found",
                    description="The BackgroundTasks cog does not have a task by that name."))
        try:
            task_object.restart()
        except AttributeError:
            return await ctx.send(
                embed=Embed(
                    color=0xff0000,
                    title="Task Not Found",
                    description="The BackgroundTasks cog does not have a task by that name."))

        return await ctx.send(
            embed=Embed(
                color=0x00ff00,
                title="Task Restarted",
                description=f"Restarted task `{task}`."))

    @loop(seconds=60)
    async def status_change(self):
        activity = Activity(
            type=ActivityType.playing,
            name=f"In development")

        await self.bot.change_presence(status=Status.idle, activity=activity)
        return

        time = datetime.utcnow().strftime("%H:%M")

        if self.bot.inactive >= 5:
            status = Status.idle
        else:
            status = Status.online

        activity = Activity(
            type=ActivityType.watching,
            name=f"{time}/UTC | {self.bot.command_prefix} | {len(self.bot.guilds)}")

        await self.bot.change_presence(status=status, activity=activity)

    @loop(seconds=297.5)
    async def save_data(self):
        print("[AST: ... Saving, do not quit...", end="\r")
        await sleep(2)
        print("[AST: !!! Saving, do not quit...", end="\r")

        if self.bot.use_firebase:
            self.bot.database.update(self.bot.user_data)

        else:
            with open("Files/user_data.json", "w") as f:
                user_data = dump(self.bot.user_data, f)

        self.bot.inactive = self.bot.inactive + 1
        time = datetime.now().strftime("%H:%M, %m/%d/%Y")
        print(f"[AST: {time}] Running.")
    
    @loop(minutes=30)
    async def del_update_stats(self):
        """ This automatically updates your server count to Discord Extreme List every 30 minutes. """
        await self.bot.wait_until_ready()
        async with ClientSession() as session:
            async with session.post(f'https://api.discordextremelist.xyz/v2/bot/{self.bot.user.id}/stats',
            headers={'Authorization': self.bot.auth['DEL_TOKEN'], # Make sure you put your API Token Here
            "Content-Type": 'application/json'},
            data=dumps({'guildCount': len(self.bot.guilds)
            })) as r:
                js = await r.json()
                if js['error'] == True:
                    print(f'Failed to post to discordextremelist.xyz\n{js}')
    
    @loop(minutes=30)
    async def discords_update_stats(self):
        await self.discords.post_servers()

    @Cog.listener()  # Callback with response code for the above loop
    async def on_discords_server_post(self, status):
        if status != 200:
            print(f"[HRB] Failed to post the server count to Discords.com. HTTP code {status}")

    @status_change.before_loop
    async def sc_wait(self):
        await self.bot.wait_until_ready()
        await sleep(30)

    @save_data.before_loop
    async def sd_wait(self):
        await self.bot.wait_until_ready()
        await sleep(15)
    
    def cog_unload(self):
        self.status_change.cancel()
        self.save_data.cancel()
        self.del_update_stats.cancel()
        self.discords_update_stats.cancel()

async def setup(bot):
    await bot.add_cog(BackgroundTasks(bot))