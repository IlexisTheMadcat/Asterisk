# IMPORTS
from os import walk, remove
from os.path import exists, join
from json import load, dump
from sys import exc_info
from copy import deepcopy
import json
from turtle import rt

from discord import __version__, Activity, ActivityType, Intents
from discord.enums import Status
from discord.permissions import Permissions
from discord.utils import oauth_url
from discord.ext.commands import ExtensionAlreadyLoaded

from utils.classes import Bot
from utils.errorlog import ErrorLog
from utils.FirebaseDB import FirebaseDB


DATA_DEFAULTS = {
    "UserData": {
        "UID": {  
            "Settings": {  # User Settings dict
                "AcceptingFriends": True,
                # Users can friend each other exclusively to the bot.

                "CustomAvatarURL": "about:blank",  # str(URL)
                # The custom avatar used by the bot with webhooks.

                "NotificationsDue": {
                    "FirstTime": False,
                },  # dict({str:bool})
                # A notification sent to users when they use a command for the first time.
                # These are set to true after being executed. Resets by command.
            },
            "Character": {
                "requires_setup": True,  # Users must set up before being able to use Asterisk to its fullest. It's pretty simple for now.

                "Name": "...",  # Users can use a custom name or "useDiscordName" to use use the user's Discord username.
                "Gender": "...",  # Female, Male, Other, Undefined
                "Race": "...",  # Human, Nekojin

                # Current, Level Max
                "Life": (100, 100),  # How much damage the user can take before being eliminated.
                "Prana": (100, 100),  # Used for most attacks
                "Attack": 100,  # Determines which player starts first and who has priority over certain attacks.
                "Insight": 100,  # Boosts prana regreneration, attack, and defense
                "Speed": 10,  # Determines which player gets priority over evasion/retaliation

                # Generic item stats include:
                # name, type, faction, rarity

                # Weapon stats include:
                # damage, additional defense, bonuses, special effects, experience

                # Armor stats include:
                # defense, bonuses, special effects, experience

                "Skill": {},  # Skills and tactics can be added here in the form of {"Skill Name": level}

                "Weapons": [None, None],  # list(item or None)
                "Abilities": [None, None, None, None, None],  # list(item or None)
                "Armor": [None, None, None, None, None, None],  # list(item or None)
                "Items": [[None, None, None, None, None],
                          [None, None, None, None, None]],  # list(item or None)
                "Storage": [None]  # list(item or None)
            },

            "Friend Requests": [331551368789622784],  # list(int(UID))
            "Friends": [],  # list(int(UID))
            # Users will start with having the developer as their first friend through the tutorial.
            # They can use this to contact the developer wirelessly. 
            
            "Location": (14, 14)  # New users start in Hotel Elnath, the center.
        }
    },
    "Tokens": {  # Replace ONLY for initialization
        "BOT_TOKEN": "xxx"  # str(token)
    },
    "config": {
        "debug_mode": False,
        # Print exceptions to stdout.

        "error_log_channel": 734499801697091654,
        # The channel that errors are sent to.

        "first_time_tip": "👋 It appears to be your first time using this bot!\n"
                          "ℹ️ For more information and help, please use the `a!help` command. For brief legal information, please use the `a!legal` command.",
    }
}

INIT_EXTENSIONS = [
    "admin",
    "background",
    "classes",
    "commands",
    "events",
    "help",
    "repl",
]

# 0 = use JSON
# 1 = use Firebase
DATA_CLOUD = 0

if DATA_CLOUD:
    if exists("Files/ServiceAccountKey.json"):
        key = load(open("Files/ServiceAccountKey.json", "r"))
    else:
        raise FileNotFoundError("Could not find ServiceAccountKey.json.")

    db = FirebaseDB(
        "https://asterisk-database-default-rtdb.firebaseio.com/", 
        fp_accountkey_json=key)

    user_data = db.copy()

else:
    with open("Files/user_data.json", "r") as f:
        db = None
        user_data = load(f)

# Check the database
for key in DATA_DEFAULTS:
    if key not in user_data:
        user_data[key] = DATA_DEFAULTS[key]
        print(f"[MISSING VALUE] Data key '{key}' missing. "
              f"Inserted default '{DATA_DEFAULTS[key]}'")
found_data = deepcopy(user_data)  # Duplicate to avoid RuntimeError exception
for key in found_data:
    if key not in user_data:
        user_data.pop(key)  # Remove redundant data
        print(f"[REDUNDANCY] Invalid data \'{key}\' found. "
              f"Removed key from file.")
del found_data  # Remove variable from namespace

config_data = user_data["config"]
# Check the bot config
for key in DATA_DEFAULTS['config']:
    if key not in config_data:
        config_data[key] = DATA_DEFAULTS['config'][key]
        print(f"[MISSING VALUE] Config '{key}' missing. "
              f"Inserted default '{DATA_DEFAULTS['config'][key]}'")
found_data = deepcopy(config_data)  # Duplicate to avoid RuntimeError exception
for key in found_data:
    if key not in DATA_DEFAULTS['config']:
        config_data.pop(key)  # Remove redundant data
        print(f"[REDUNDANCY] Invalid config \'{key}\' found. "
              f"Removed key from file.")
del found_data  # Remove variable from namespace

if DATA_CLOUD:
    db.update(user_data)
else:
    with open("Files/user_data.json", "w") as f:
        dump(user_data, f)

intents = Intents.default()
intents.message_content = True

bot = Bot(
    description="An MMORPG parody of the anime `The Asterisk War`.",
    owner_ids=[331551368789622784],  # Ilexis
    status=Status.idle,
    activity=Activity(type=ActivityType.watching, name="duels in the city of Asterisk."),
    command_prefix="a!",

    config=config_data,
    database=db,
    user_data=user_data,   
    defaults=DATA_DEFAULTS,
    auth=user_data["Tokens"],
    use_firebase=DATA_CLOUD,
    intents=intents
)

# If a custom help command is created:
bot.remove_command("help")

print(f"[BOT INIT] Running in: {bot.cwd}\n"
      f"[BOT INIT] Discord API version: {__version__}")

mypath = "Storage"
for root, dirs, files in walk(mypath):
    for file in files:
        remove(join(root, file))

@bot.event
async def on_ready():
    app_info = await bot.application_info()
    bot.owner = app_info.owner

    permissions = Permissions()
    permissions.update(
        send_messages=True,
        embed_links=True,
        add_reactions=True,
        manage_channels=True,
        manage_webhooks=True,
        manage_roles=True)

    # Add the ErrorLog object if the channel is specified
    if bot.config["error_log_channel"]:
        error_channel = await bot.fetch_channel(bot.config["error_log_channel"])
        bot.errorlog = ErrorLog(bot, error_channel)
    
    print("\n"
          "#-------------------------------#\n"
          "| Loading initial cogs...\n"
          "#-------------------------------#")

    for cog in INIT_EXTENSIONS:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"| Loaded initial cog {cog}")
        except Exception as e:
            try:
                print(f"| Failed to load extension {cog}\n|   {type(e.original).__name__}: {e.original}")
            except AttributeError:
                print(f"| Failed to load extension {cog}\n|   {type(e).__name__}: {e}")
            error = exc_info()
            if error:
                await bot.errorlog.send(error, event="Load Initial Cog")
                
    print(f"#-------------------------------#\n"
          f"| Successfully logged in.\n"
          f"#-------------------------------#\n"
          f"| User:      {bot.user}\n"
          f"| User ID:   {bot.user.id}\n"
          f"| Owner:     {bot.owner}\n"
          f"| Guilds:    {len(bot.guilds)}\n"
          f"| OAuth URL: {oauth_url(app_info.id, permissions=permissions)}\n"
          f"#------------------------------#\n")

if __name__ == "__main__":
    bot.run()