# import os
# from asyncio import sleep
# from asyncio.exceptions import TimeoutError
# from textwrap import shorten
from contextlib import suppress
from copy import deepcopy
from typing import Literal

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

    async def check_data(self, interaction, ephemeral = False):
        """ Ensure the user has a place to store data in the bot. If called, interaction will always be deferred as "thinking". """
        await interaction.response.defer(thinking = True, ephemeral=ephemeral)

        if str(interaction.user.id) in self.bot.user_data["UserData"]:
            return True

        class ConfirmCreate(ui.View):
            def __init__(self, bot, interaction):
                super().__init__(timeout=15)
                self.value = None
                self.bot = bot
                self.interaction = interaction
            
            @ui.button(label="Create", style=ButtonStyle.primary, custom_id="button1")
            async def Create_button(self, button_interaction, button_object):
                if button_interaction.user.id == self.interaction.user.id:
                    print(f"[HRB] {button_interaction.user} ({button_interaction.user.id}) created data for Asterisk.")
                    emb = Embed(
                        title="✅ Data Creation Success",
                        description="Your data related to Asterisk now has a place to be stored."
                    )
                    
                    button_object.style = ButtonStyle.success
                    for component in self.children:
                        component.disabled = True
                    await button_interaction.response.edit_message(embed=emb, view=self, delete_after = 5)
                    self.bot.user_data["UserData"][str(interaction.user.id)] = deepcopy(self.bot.defaults["UserData"]["UID"])
                    self.value = True
                    self.stop()

            @ui.button(label="Cancel", style=ButtonStyle.secondary, custom_id="button2")
            async def cancel_button(self, button_interaction, button_object):
                if button_interaction.user.id == self.interaction.user.id:
                    await self.interaction.followup.send("I cant proceed without data storage permission.")
                    emb = Embed(
                        title="❌ Data Creation Cancelled",
                        description="Nothing about you was saved.\n"
                                    "Please note that you can't use the bot without proceeding."
                    )
                    for component in self.children:
                        component.disabled = True
                    await button_interaction.response.edit_message(embed=emb, view=self, delete_after = 5)
                    self.value = False
                    self.stop()

            async def on_timeout(self):
                for component in self.children:
                    component.disabled = True
                self.children[0].label = "Timeout"
                await self.interaction.followup.send("I cant proceed without data storage permission.")
                await self.message.edit(embed=emb, view=self, delete_after = 5)
                self.value = False
                self.stop()

        emb = Embed(
            title="Confirm Data Creation",
            description="To play Asterisk, you must allow it to store information related to your Discord account.\n"
                        "If you wish to continue, press Create. Otherwise, Cancel."
        )
        view = ConfirmCreate(self.bot, interaction)
        dm_channel = await interaction.user.create_dm()
        view.message = await interaction.channel.send(interaction.user.mention, embed=emb, view=view)
        await view.wait()

        self.bot.inactive = 0
        return view.value

    @slash_command(name="sync", description="Prioritize new command updates on this server.")
    async def sync_commands(self, interaction):
        if not await self.check_data(interaction, ephemeral=True): return

        await self.bot.tree.sync(guild=interaction.guild)
        newline = "\n"
        await interaction.followup.send(f"Commands synced.", ephemeral=True)
    
    @slash_command(name="test", description="Test the response of Asterisk.")
    async def test(self, interaction):
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
            async def continue_button(self, button_interaction, button_object):
                if button_interaction.user.id == interaction.user.id:
                    button_object.disabled = True
                    button_object.label = "Success!"
                    button_object.emoji = "✅"
                    await button_interaction.response.edit_message(embed=Embed(description="Button complete. (3/3)"), view=self)
                    self.value = True
                    self.stop()

            async def on_timeout(self):
                self.children[0].disabled = True
                self.children[0].label = "Timeout!"
                self.children[0].emoji = "❌"
                await self.message.edit(embed=Embed(description="Button timed out. (3/3)"), view=self)
                self.stop()
        
        view = TestButton()
        await interaction.response.send_message(embed=Embed(description="Waiting for button... (3/3)"), view=view)
        view.message = await interaction.original_response()
        await view.wait()

        await interaction.followup.send("Test complete.", ephemeral=True)

        print(f"{interaction.user} ({interaction.user.id}) tested.")

    # 
    @slash_command(name="setup_char", description="Set up your character in one line. You can do this at any time.")
    async def setup_char(self, interaction): 
        """ Start the character creation process """
        if not await self.check_data(interaction, ephemeral=False): return

        await interaction.followup.send("NotImplemented", ephemeral=True)
    
    @slash_command(name="character", description="Show your character information.")
    async def character(self, interaction):
        """ Show character information """
        if not await self.check_data(interaction, ephemeral=False): return

        character = self.bot.user_data["UserData"][str(interaction.user.id)]["Character"]
        if character["requires_setup"]:
            return await interaction.followup.send("You haven't set up your character yet! To do so, run `/setup_char`.")

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
        if not skill_lines: skill_lines.insert(0, "Skills are aquired as you play and discover.")
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
            value="..."
        )

        await interaction.followup.send(embed=emb)

    @slash_command(name="create_client")
    async def create_client(self, interaction):
        pass

    @slash_command(name="delete_data", description="Remove all of your data from Asterisk.")
    async def delete_user_data(self, interaction):
        if str(interaction.user.id) not in self.bot.user_data["UserData"]:
            return await interaction.response.send_message("You dont have any data to remove from Asterisk.", ephemeral=True)

        class ConfirmReset(ui.View):
            def __init__(self, bot, interaction):
                super().__init__(timeout=15)
                self.value = None
                self.bot = bot
                self.interaction = interaction
            
            @ui.button(label="Continue", style=ButtonStyle.danger, custom_id="button1")
            async def confirm_button(self, button_interaction, button_object):
                if button_interaction.user.id == self.interaction.user.id:
                    self.bot.user_data["UserData"].pop(str(self.interaction.user.id))
                    print(f"[HRB] {button_interaction.user} ({button_interaction.user.id}) popped their data from Asterisk.")
                    emb = Embed(
                        title="✅ Reset Success",
                        description="Your data has been removed. Thank you for using Asterisk!"
                    )
                    await button_interaction.response.edit_message(embed=emb, view=None)
                    self.stop()

            @ui.button(label="Cancel", style=ButtonStyle.secondary, custom_id="button2")
            async def cancel_button(self, button_interaction, button_object):
                if button_interaction.user.id == self.interaction.user.id:
                    emb = Embed(
                        title="<:SeidoukanEmblem:839250137838649396> Reset Cancelled",
                        description="Your data hasn't been touched."
                    )
                    await button_interaction.response.edit_message(embed=emb, view=None)
                    self.stop()

            async def on_timeout(self):
                for component in self.children:
                    component.disabled = True
                await self.message.edit(embed=emb, view=self)
                self.stop()

        emb = Embed(
            title="⚠️ Deleting User Data",
            description="You've requested to remove all of your data from Asterisk's database.\n"
                        "If you wish to continue, press Confirm. Otherwise, Cancel."
        )
        view = ConfirmReset(self.bot, interaction)
        await interaction.response.send_message(embed=emb, view=view, ephemeral=True)
        view.message = await interaction.original_response()

        await view.wait()
        return

async def setup(bot):
    await bot.add_cog(Commands(bot))
