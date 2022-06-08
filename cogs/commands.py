# import os
# from asyncio import sleep
# from asyncio.exceptions import TimeoutError
# from textwrap import shorten
from contextlib import suppress
from copy import deepcopy
from typing import Literal

# from discord import Forbidden
from discord import ui, ButtonStyle
from discord.errors import Forbidden
from discord.ext.commands.cog import Cog
from discord.ext.commands.core import (
    has_permissions, 
    bot_has_permissions, 
    command, is_owner
)
from discord import Interaction
from discord.app_commands import command as slash_command

from utils.classes import Embed
from utils.misc import emoji_value_bar, health_bars, prana_bars

class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot

        self.multiplayer_instances = []
        self.client_instances = []

    async def check_data(self, interaction):
        if str(interaction.user.id) not in self.bot.user_data["UserData"]:
            self.bot.user_data["UserData"][str(interaction.user.id)] = deepcopy(self.bot.defaults["UserData"]["UID"])

        if not self.bot.user_data["UserData"][str(interaction.user.id)]["Settings"]["NotificationsDue"]["FirstTime"]:
            with suppress(Forbidden):
                await interaction.user.send(embed=Embed(
                    title="First Time Interaction Notification",
                    description=self.bot.config["first_time_tip"]))
            
            self.bot.user_data["UserData"][str(interaction.user.id)]["Settings"]["NotificationsDue"]["FirstTime"] = True

        self.bot.inactive = 0
        return

    @slash_command(name="sync", description="Prioritize new command updates on this server.")
    async def sync_commands(self, interaction):
        await self.check_data(interaction)

        await self.bot.tree.sync(guild=interaction.guild)
        await interaction.response.send_message("Commands synced.")
    
    @slash_command(name="test", description="Test the response of Asterisk.")
    async def test(self, interaction: Interaction):
        await self.check_data(interaction)

        await interaction.response.defer(thinking=True)

        try:
            await interaction.channel.send("Done (1/3).")
        except Exception:
            await interaction.user.send("(1/3) I can't send messages there.")
        
        try:
            await interaction.channel.send(embed=Embed(description="Done (2/3)."))
        except Exception:
            await interaction.channel.send("(2/3) I can't send embeds in here.")

        class TestButton(ui.View):
            def __init__(self):
                super().__init__(timeout=5)
                self.value = None
            
            @ui.button(label="Click to test.", style=ButtonStyle.primary, emoji="🔘", custom_id="test")
            async def continue_button(self, button, interaction):
                if interaction.user.id == interaction.user.id:
                    button.disabled = True
                    button.label = "Success!"
                    button.emoji = "✅"
                    await interaction.response.edit_message(embed=Embed(description="Button complete. (3/3)"), view=self)
                    self.value = True
                    self.stop()

            async def on_timeout(self):
                self.children[0].disabled = True
                self.children[0].label = "Timeout!"
                self.children[0].emoji = "❌"
                await self.message.edit(embed=Embed(description="Button timed out. (3/3)"), view=self)
                self.stop()
        
        view = TestButton()
        view.message = await interaction.followup.send(embed=Embed(description="Waiting for button... (3/3)"), view=view)
        await view.wait()

        print(f"{interaction.user} ({interaction.user.id}) tested.")

        await interaction.followup.send("Test complete.", ephemeral=True)

    @slash_command(name="setup_char", description="Set up your character in one line. You can do this at any time.")
    async def setup_char(self, interaction, 
        name: str, 
        gender: Literal["Female", "Male", "Other", "Undefined"],
        race: Literal["Human", "Nekojin"]):
        await self.check_data(interaction)

        character = self.bot.user_data["UserData"][str(interaction.user.id)]["Character"]
        character["Name"] = name
        character["Gender"] = gender
        character["Race"] = race
        
        if character["requires_setup"] == True:
            await interaction.response.send_message(embed=Embed(description="Character created!"))
            character["requires_setup"] = False
        else:
            await interaction.response.send_message(embed=Embed(description="Character edited!"))
    
    @slash_command(name="character", description="Show your character information.")
    async def character(self, interaction):
        await self.check_data(interaction)

        character = self.bot.user_data["UserData"][str(interaction.user.id)]["Character"]
        if character["requires_setup"]:
            return await interaction.response.send_message("You haven't set up your character yet! To do so, run `/setup_char`.")

        hp = character["Life"]
        prana = character["Prana"]

        health_bar = emoji_value_bar(hp[0], hp[1], 15, health_bars)
        energy_bar = emoji_value_bar(prana[0], prana[1], 10, prana_bars)

        # combine armor and equipped weapon stats
        defense = 0
        for armor_piece in character["Armor"]:
            if not armor_piece:
                continue
            defense = defense + armor_piece["defense"]
        if character["Weapons"][0]:
            defense = defense + character["Weapons"][0]["defense"]
        
        skill_lines = []
        for name, values in character["Skill"].items():
            frac = f"{values[0]}/{values[1]}".rjust(10)
            skill_lines.append(f"`{name.ljust(10)}: {frac} |` {emoji_value_bar(values[0], values[1], 4, prana_bars)}")
        if skill_lines: skill_lines.insert(0, "Skills are aquired as you play and discover.")
        skill_lines = "\n".join(skill_lines)

        emb = Embed(
            title=character["Name"] if character["Name"] != "useDiscordName" else interaction.user,
            description=f"<:blank:899735491027554315>{health_bar}\n"
                        f"{energy_bar}\n"
                        f"Life: {hp[0]}/{hp[1]} | Prana: {prana[0]}/{prana[1]}\n"
                        f"Defense: {defense}\n"
                        f"\n"
                        f"{skill_lines}"
        ).add_field(
            inline=False,
            name="Weapons",
            value="This is a placeholder status message."
        )

        await interaction.response.send_message(embed=emb)

    @slash_command(name="create_client")
    async def create_client(self, interaction):
        pass

    @slash_command(name="reset_data", description="Remove all of your data from Asterisk.")
    async def reset_user_data(self, interaction):
        await self.check_data(interaction)

        class ConfirmReset(ui.View):
            def __init__(self, bot, inter):
                super().__init__(timeout=15)
                self.value = None
                self.bot = bot
                self.inter = inter
            
            @ui.button(label="Continue", style=ButtonStyle.danger, custom_id="button1")
            async def confirm_button(self, button, inter):
                if inter.user.id == self.inter.user.id:
                    print(f"[HRB] {inter.user} ({inter.user.id}) popped their data from Asterisk.")
                    emb = Embed(
                        title="✅ Reset Success",
                        description="Your data has been removed. Thank you for using Asterisk!"
                    )
                    await inter.response.edit_message(embed=emb, view=None)
                    self.bot.user_data["UserData"].pop(str(self.inter.user.id))
                    self.stop()

            @ui.button(label="Cancel", style=ButtonStyle.secondary, custom_id="button2")
            async def cancel_button(self, button, inter):
                if inter.user.id == self.inter.author.id:
                    emb = Embed(
                        title="<:SeidoukanEmblem:839250137838649396> Reset Cancelled",
                        description="Your data hasn't been touched."
                    )
                    await inter.response.edit_message(embed=emb, view=None)
                    self.stop()

            async def on_timeout(self):
                for component in self.children:
                    component.disabled = True
                await self.message.edit(embed=emb, view=self)
                self.stop()

        emb = Embed(
            title="⚠️ Resetting User Data",
            description="You've requested to remove all of your data from Asterisk's database.\n"
                        "If you wish to continue, press Confirm. To leave your data untouched, press Cancel."
        )
        view = ConfirmReset(self.bot, interaction)
        view.message = await interaction.response.send_message(embed=emb, view=view)
        await view.wait()
        return

async def setup(bot):
    await bot.add_cog(Commands(bot))
