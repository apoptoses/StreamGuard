import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from flask import Flask
import threading
from app import send_discord_message, get_current_streamer
from commands import BotCommands
from storage import init_db, get_all_guild_ids

# load environment variables
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

role_id = int(os.getenv('DISCORD_ROLE_ID', 0))
channel_id = int(os.getenv('DISCORD_CHANNEL_ID', 0))

# discord bot setup
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True  # enable message content intent
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# flask app setup
app = Flask(__name__)

@app.route("/")
def home():
    return "Discord Bot is Running!"

def run_flask_app():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
@bot.event
async def on_ready():
    await bot.add_cog(BotCommands(bot))
    print(f"[ INFO ] Registered commands: {[command.name for command in bot.commands]}")
    print(f"[ INFO ] Logged in as: {bot.user} ✅")
    print(f"[ INFO ] Bot ID: {bot.user.id}")
    print(f"[ INFO ] Connected to {len(bot.guilds)} server(s)")
    print(f"[ INFO ] Ping: {round(bot.latency * 1000)} ms")
    update_status.start()
    heartbeat.start()

@bot.event
async def on_message(message):
    guild_id = message.guild.id if message.guild else "DM"
    print(f"Received message: {message.content} | Guild ID: {guild_id}")
    await bot.process_commands(message)

@tasks.loop(seconds=300)
async def update_status():
    # update status for each guild
    for guild in bot.guilds:
        streamer = get_current_streamer(guild.id)
        activity = discord.Activity(name=f"{streamer} on Twitch" if streamer else "you", type=discord.ActivityType.watching)
        await bot.change_presence(activity=activity, status=discord.Status.online)

@tasks.loop(seconds=30)
async def heartbeat():
    print(f"[ HEARTBEAT ] Bot is alive at {discord.utils.utcnow()}")

if __name__ == "__main__":
    init_db()
    # initialize notified_streams for each guild
    guild_ids = get_all_guild_ids()  # Retrieve all guild IDs from the database
    for guild_id in guild_ids:
        # ensure each guild has its own set of notified streams
        from app import notified_streams
        notified_streams[guild_id] = set()

    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    if DISCORD_BOT_TOKEN:
        bot.run(DISCORD_BOT_TOKEN)
    else:
        print("[ ERROR ] DISCORD_BOT_TOKEN not found. Make sure to set it in the .env file.")
