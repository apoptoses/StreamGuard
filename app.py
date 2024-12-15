import os
import time
import threading
import requests
from dotenv import load_dotenv
from storage import get_streamers, init_db, get_all_guild_ids

# load environment variables
load_dotenv()

# initialize the database
init_db()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')

CHECK_INTERVAL = 60
TWITCH_API_URL = "https://api.twitch.tv/helix/streams"

notified_streams = {}

def get_oauth_token():
    """Fetch OAuth token from Twitch."""
    url = "https://id.twitch.tv/oauth2/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=payload)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching OAuth token: {e}")
        print(f"Response content: {response.content.decode()}")
        raise
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

def send_discord_message(channel_id, message):
    """Send a message to Discord."""
    discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
    url = f"https://discord.com/api/channels/{channel_id}/messages"
    headers = {
        'Authorization': f'Bot {discord_bot_token}',
        'Content-Type': 'application/json'
    }
    payload = {'content': message}
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

def monitor_streams():
    """Monitor Twitch streams and notify on Discord."""
    global notified_streams
    access_token = get_oauth_token()
    while True:
        # iterate over each guild and its streamers
        for guild_id in notified_streams.keys():
            streamers = get_streamers(guild_id)
            for streamer in streamers:
                stream_info = check_stream_status(access_token, streamer)
                if stream_info and streamer not in notified_streams[guild_id]:
                    message = (
                        f"**{streamer} is live!** 🎮\n\n"
                        f"**Title:** {stream_info['title']}\n\n"
                        f"**Category:** {stream_info['category']}\n\n"
                        f"[Watch now!]({stream_info['url']})"
                    )
                    from bot import send_message_to_channel  # avoid circular imports
                    send_message_to_channel(message)
                    notified_streams[guild_id].add(streamer)
                elif not stream_info:
                    notified_streams[guild_id].discard(streamer)
        time.sleep(CHECK_INTERVAL)

def get_current_streamer(guild_id):
    """Fetch the name of the currently streaming Twitch streamer for a guild."""
    if guild_id in notified_streams and notified_streams[guild_id]:
        return list(notified_streams[guild_id])[0]  # return the first live streamer
    return None

if __name__ == "__main__":
    # initialize notified_streams for each guild
    guild_ids = get_all_guild_ids()  # retrieve all guild IDs from the database
    for guild_id in guild_ids:
        notified_streams[guild_id] = set()
    # start Twitch monitoring in a separate thread
    monitor_thread = threading.Thread(target=monitor_streams)
    monitor_thread.daemon = True
    monitor_thread.start()