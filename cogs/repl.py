"""
Cog created by SirThane @ Github
Edited by SUPERMECHM500 @ Repl.it
"""

import random
from inspect import isawaitable
from asyncio import sleep
from contextlib import suppress
from asyncio import TimeoutError

import discord
from discord.colour import Colour
from discord.embeds import Embed
from discord.ext.commands.cog import Cog
from discord.ext.commands.context import Context
from discord.ext.commands.core import command, group, is_owner
from discord.errors import NotFound, Forbidden

from utils.classes import Bot, Paginator


MD = "```py\n{0}\n```"


class REPL(Cog):
    """Read-Eval-Print Loop debugging commands"""

    def __init__(self, bot: Bot):
        self.bot = bot

        self.ret = None
        self._env_store = dict()
        self.emb_pag = Paginator(
            page_limit=1014,
            trunc_limit=1850,
        )

    def emb_dict(self, title: str, desc: str) -> dict:
        d = {
            "title": title,
            "description": desc,
            "fields": list()
        }
        return d

    def _env(self, ctx: Context):
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'message': ctx.message,
            'guild': ctx.message.guild,
            'channel': ctx.message.channel,
            'author': ctx.message.author,
            'discord': discord,
            'random': random,
            'ret': self.ret,
        }
        env.update(globals())
        env.update(self._env_store)
        return env

    @is_owner()
    @group(name='env')
    async def env(self, ctx: Context):
        pass

    @is_owner()
    @env.command(name='update', aliases=['store', 'add', 'append'])
    async def _update(self, ctx: Context, name: str):
        """Add `ret` as a new object to custom REPL environment"""

        if name:
            self._env_store[name] = self.ret
            em = Embed(title='Environment Updated', color=Colour.green())
            em.add_field(name=name, value=repr(self.ret))

        else:
            em = Embed(
                title='Environment Update',
                description='You must enter a name',
                color=Colour.red()
            )

        await ctx.send(embed=em)

    @is_owner()
    @env.command(name='remove', aliases=['rem', 'del', 'pop'])
    async def _remove(self, ctx: Context, name: str):
        if name:
            v = self._env_store.pop(name, None)
        else:
            v = None
            name = 'You must enter a name'
        if v:
            emb = Embed(title='Environment Item Removed', color=Colour.green())
            emb.add_field(name=name, value=repr(v))
        else:
            emb = Embed(title='Environment Item Not Found', description=name, color=Colour.red())
        await ctx.send(embed=emb)

    @is_owner()
    @env.command(name='list')
    async def _list(self, ctx: Context) -> None:
        if len(self._env_store.keys()):
            emb = Embed(title='Environment Store List', color=Colour.green())
            for k, v in self._env_store.items():
                emb.add_field(name=k, value=repr(v))
        else:
            emb = Embed(title='Environment Store List', description='Environment Store is currently empty',
                        color=Colour.green())
        await ctx.send(embed=emb)

    @is_owner()
    @command(hidden=True, name='eval')
    async def _eval(self, ctx: Context, *, code: str) -> None:
        """Run eval() on an input."""

        code = code.strip('` ')
        emb = self.emb_dict(title='Eval on', desc=MD.format(code))

        try:
            result = eval(code, self._env(ctx))
            if isawaitable(result):
                result = await result
            self.ret = result
            self.emb_pag.set_headers(['Yielded result:'])
            emb['colour'] = 0x00ff00
            for h, v in self.emb_pag.paginate(result):
                field = {
                    'name': h,
                    'value': MD.format(v),
                    'inline': False
                }
                emb['fields'].append(field)

        except Exception as e:
            emb['colour'] = 0xff0000
            field = {
                'name': 'Yielded exception "{0.__name__}":'.format(type(e)),
                'value': '{0}'.format(e),
                'inline': False
            }
            emb['fields'].append(field)

        embed = Embed().from_dict(emb)

        eval_message = await ctx.channel.send(embed=embed)

        try:
            await eval_message.add_reaction("❌")
        except Forbidden:
            return
        else:
            def check(reaction, user):
                return all((reaction.message.id == eval_message.id, str(reaction.emoji) == "❌", user == ctx.author))
            
            try:
                await self.bot.wait_for("reaction_add", timeout=30, check=check)
            except TimeoutError:
                with suppress(NotFound):
                    await eval_message.remove_reaction("❌", self.bot.user)
            else:
                await eval_message.remove_reaction("❌", self.bot.user)
                with suppress(Forbidden):
                    await eval_message.remove_reaction("❌", ctx.author)
                await eval_message.edit(embed=Embed(description=":eye_in_speech_bubble: Caller has hidden eval output.", color=0xff0000))
                await sleep(0.2)
                await eval_message.edit(embed=Embed(description=":eye_in_speech_bubble: Caller has hidden eval output.", color=0x000000))
                await sleep(0.2)
                await eval_message.edit(embed=Embed(description=":eye_in_speech_bubble: Caller has hidden eval output.", color=0xff0000))
                await sleep(0.2)
                await eval_message.edit(embed=Embed(description=":eye_in_speech_bubble: Caller has hidden eval output.", color=0x000000))


async def setup(bot: Bot):
    await bot.add_cog(REPL(bot))
