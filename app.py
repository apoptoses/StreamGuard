import os
import requests
import time
import threading
from flask import Flask, send_from_directory
from discord.ext import commands, tasks
import discord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twitch API Credentials
CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

# Discord Bot Credentials
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')

# Twitch and Discord settings
STREAMERS = ['kronk0133','p4nduhs1 ']
CHECK_INTERVAL = 60
TWITCH_API_URL = "https://api.twitch.tv/helix/streams"
DISCORD_API_URL = f"https://discord.com/api/channels/{DISCORD_CHANNEL_ID}/messages"

# Flask app setup
app = Flask(__name__, static_folder='.')

@app.route("/")
def home():
    """Basic route to confirm service is running."""
    return "Twitch Monitor Service is Running!"

@app.route("/discord")
def discord_home():
    """Serve the index.html for Discord bot."""
    return send_from_directory('.', 'index.html')

# Discord bot setup
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Status and heartbeat
status_messages = ["🎧 Listening to Spotify", "🎮 Playing VALORANT"]
status_types = [discord.Status.dnd, discord.Status.idle]
current_status_index = 0
current_type_index = 0

@tasks.loop(seconds=10)
async def update_status():
    global current_status_index, current_type_index
    current_status = status_messages[current_status_index]
    current_type = status_types[current_type_index]
    
    # Use "Listening" activity instead of "Playing"
    activity = discord.Activity(name=current_status, type=discord.ActivityType.listening)
    await bot.change_presence(activity=activity, status=current_type)

    print(f"[ STATUS ] Updated status to: {current_status} ({current_type})")
    current_status_index = (current_status_index + 1) % len(status_messages)
    current_type_index = (current_type_index + 1) % len(status_types)

@tasks.loop(seconds=30)
async def heartbeat():
    print(f"[ HEARTBEAT ] Bot is alive at {discord.utils.utcnow()}")

@bot.event
async def on_ready():
    print(f"[ INFO ] Logged in as: {bot.user} ✅")
    print(f"[ INFO ] Bot ID: {bot.user.id}")
    print(f"[ INFO ] Connected to {len(bot.guilds)} server(s)")
    print(f"[ INFO ] Ping: {round(bot.latency * 1000)} ms")
    update_status.start()
    heartbeat.start()

def get_oauth_token():
    """Fetch OAuth token from Twitch."""
    url = "https://id.twitch.tv/oauth2/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    return response.json()['access_token']

def check_stream_status(access_token, streamer):
    """Check if a Twitch stream is live."""
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {access_token}'
    }
    params = {'user_login': streamer}
    response = requests.get(TWITCH_API_URL, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    if data['data']:
        return {
            'title': data['data'][0]['title'],
            'category': data['data'][0]['game_name'],
            'url': f"https://www.twitch.tv/{streamer}"
        }
    return None

def send_discord_message(message):
    """Send a message to Discord."""
    headers = {
        'Authorization': f'Bot {DISCORD_BOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {'content': message}
    response = requests.post(DISCORD_API_URL, headers=headers, json=payload)
    response.raise_for_status()

def monitor_streams():
    """Monitor Twitch streams and notify on Discord."""
    access_token = get_oauth_token()
    notified_streams = set()

    while True:
        for streamer in STREAMERS:
            stream_info = check_stream_status(access_token, streamer)
            if stream_info and streamer not in notified_streams:
                message = (
                    f"**{streamer} is live!** 🎮\n\n"
                    f"**Title:** {stream_info['title']}\n\n"
                    f"**Category:** {stream_info['category']}\n\n"
                    f"[Watch now!]({stream_info['url']})"
                )
                send_discord_message(message)
                notified_streams.add(streamer)
            elif not stream_info:
                notified_streams.discard(streamer)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Start Twitch monitoring in a separate thread
    monitor_thread = threading.Thread(target=monitor_streams)
    monitor_thread.daemon = True
    monitor_thread.start()

    # Start the Flask web server in a separate thread
    from threading import Thread
    def run_flask():
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start Discord bot
    if DISCORD_BOT_TOKEN:
        bot.run(DISCORD_BOT_TOKEN)
    else:
        print("[ ERROR ] DISCORD_BOT_TOKEN not found. Make sure to set it in the .env file.")
