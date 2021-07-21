# import os
# from asyncio import sleep
# from asyncio.exceptions import TimeoutError
# from textwrap import shorten
# from contextlib import suppress

# from discord import Forbidden
from discord.ext.commands.cog import Cog
from discord.ext.commands.core import (
    has_permissions, 
    bot_has_permissions, 
    command
)

from utils.classes import Embed, PDA

class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @command(name="test")
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def test(self, ctx):
        try:
            await ctx.send("Done (1/2).")
        except Exception:
            await ctx.author.send("(1/2) I can't send messages there.")
        
        try:
            await ctx.send(embed=Embed(title="Done (2/2)."))
        except Exception:
            await ctx.send("(2/2) I can't send embeds in here.")
    
    @command(name="summon_pda")
    @has_permissions(send_messages=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def create_interactive(self, ctx):
        interactive = PDA(self.bot, ctx)
        await interactive.setup()
        await interactive.start()


def setup(bot):
    bot.add_cog(Commands(bot))
