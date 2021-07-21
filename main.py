# IMPORTS
from os import walk, remove
from os.path import exists, join
from json import load
from sys import exc_info
from copy import deepcopy
from discord_components import DiscordComponents

from discord import __version__, Activity, ActivityType, Intents
from discord.enums import Status
from discord.permissions import Permissions
from discord.utils import oauth_url

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
            "Inventory": {
                "Weapons": [None, None],  # list(WeaponClass or None)
                "Abilities": [None, None, None, None, None],  # list(AbilityClass or None)
                "Armor": [None, None, None, None, None, None],  # list(ArmorClass or None)
                "Items": [[None, None, None, None, None],
                          [None, None, None, None, None]],  # list(ItemClass or None)
                "Backpack": None  # BackpackClass or None
            },
            "Friends": [331551368789622784],  # list(int(UID))
            # Users will start with having the developer as their first friend.
            # They can use this to contact the developer wirelessly. 
            
            "Location": ((3,3), (5,5))  # New users start in Hotel Elnath, the center.
        }
    },
    "GuildData": {
        "GID": {
            "Settings": {

            }
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
    "commands",
    "events",
    "help",
    "repl",
    "web"
]

if exists("Workspace/Files/ServiceAccountKey.json"):
    key = load(open("Workspace/Files/ServiceAccountKey.json", "r"))
else:  # If it doesn't exists assume running on replit
    try:
        from replit import db
        key = dict(db["SAK"])
    except Exception:
        raise FileNotFoundError("Could not find ServiceAccountKey.json.")

db = FirebaseDB(
    "https://asterisk-database-default-rtdb.firebaseio.com/", 
    fp_accountkey_json=key)

user_data = db.copy()
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
              f"Removed key from database.")
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
              f"Removed key from database.")
del found_data  # Remove variable from namespace

db.update(user_data)

intents = Intents.default()

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
    auth=db["Tokens"],
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
    bot.owner = bot.get_user(app_info.owner.id)

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
            bot.load_extension(f"cogs.{cog}")
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
          f"| OAuth URL: {oauth_url(app_info.id, permissions)}\n"
          f"#------------------------------#\n")

if __name__ == "__main__":
    bot.run()