# IMPORTS
from sys import exc_info
from contextlib import suppress
from copy import deepcopy

from discord.message import Message
from discord.errors import Forbidden, HTTPException
from discord.ext.commands.cog import Cog
from discord.ext.commands.context import Context
from discord.ext.commands.errors import (
    BotMissingPermissions,
    CommandNotFound,
    CommandOnCooldown,
    MissingPermissions,
    MissingRequiredArgument,
    NotOwner, BadArgument,
    CheckFailure)

# for retrofitting
from discord.app_commands import command as slash_command, describe
from discord.app_commands.checks import cooldown

from utils.classes import Embed

class Events(Cog):
    def __init__(self, bot):
        self.bot = bot

    # Interaction events
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_interaction(self, interaction):
        pass

    @cooldown(1, 2)
    @slash_command(name="r", description="Run a legacy bot command. Original prefix is optional.")
    @describe(command="Input legacy command message.")
    async def run(self, interaction, *, command: str):
        ctx = await Context.from_interaction(interaction)

        if command.startswith(self.bot.command_prefix):
            ctx.message.content = command
        else:
            ctx.message.content = self.bot.command_prefix+command

        await interaction.response.defer(thinking=True)

        await self.on_message(ctx.message)

        await interaction.followup.send("Command completed.")
        
    # Message events
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_message(self, msg: Message):
        # Cooldown
        if msg.author.id in self.bot.global_cooldown: return
        else: self.bot.global_cooldown.update({msg.author.id:"placeholder"})

        # Checks if the message is any attempted command.
        if msg.content.startswith(self.bot.command_prefix) and not msg.content.startswith(self.bot.command_prefix+" "):
            self.bot.inactive = 0
            await self.bot.process_commands(msg)
            return
    
    # Errors
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: Exception):
        if not isinstance(error, CommandNotFound):
            with suppress(Forbidden):
                await ctx.message.add_reaction("❌")
            
        if not isinstance(error, CommandOnCooldown) and ctx.command:
            ctx.command.reset_cooldown(ctx)
            
        if self.bot.config['debug_mode']:
            raise error.original
            
        if not self.bot.config['debug_mode']:
            msg = ctx.message
            em = Embed(title="Error", color=0xff0000)
            if isinstance(error, BotMissingPermissions):
                em.description = f"This bot is missing one or more permissions listed in `{self.bot.command_prefix}help` " \
                                 f"under `Required Permissions` or you are trying to use the command in a DM channel." \

            elif isinstance(error, MissingPermissions):
                em.description = "You are missing a required permission, or you are trying to use the command in a DM channel."

            elif isinstance(error, NotOwner):
                em.description = "That command is not listed in the help menu and is to be used by the owner only."

            elif isinstance(error, MissingRequiredArgument):
                em.description = f"\"{error.param.name}\" is a required argument for command " \
                                 f"\"{ctx.command.name}\" that is missing."

            elif isinstance(error, BadArgument):
                em.description = f"You didn't type something correctly. Details below:\n" \
                                 f"{error}"

            elif isinstance(error, CommandNotFound):
                return
            
            elif isinstance(error, CommandOnCooldown):
                await msg.author.send(embed=Embed(
                    description=f"That command is on a {round(error.cooldown.per)} second cooldown.\n"
                                f"Retry in {round(error.retry_after)} seconds."))
            
            elif isinstance(error, CheckFailure):
                return

            else:
                try:
                    em.description = f"**{type(error.original).__name__}**: {error.original}\n" \
                                    f"\n" \
                                    f"If you keep getting this error, please join the support server."
                except AttributeError:
                    em.description = f"**{type(error).__name__}**: {error}\n" \
                                    f"\n" \
                                    f"If you keep getting this error, please join the support server."
                
                # Raising the exception causes the progam 
                # to think about the exception in the wrong way, so we must 
                # target the exception indirectly.
                if not self.bot.config["debug_mode"]:
                    try:
                        try:
                            raise error.original
                        except AttributeError:
                            raise error
                    except Exception:
                        error = exc_info()

                    await self.bot.errorlog.send(error, event=f"Command: {ctx.command.name}")
                else:
                    try:
                        raise error.original
                    except AttributeError:
                        raise error
            
            try:
                await ctx.send(embed=em)
            except Forbidden:
                with suppress(Forbidden):
                    await ctx.author.send(
                        content="This error was sent likely because I "
                                "was blocked from sending messages there.",
                        embed=em)

async def setup(bot):
    await bot.add_cog(Events(bot))