import os
import requests
import asyncio
import logging
from dotenv import load_dotenv
from discord.errors import Forbidden, NotFound, HTTPException
from storage import get_streamers, init_db, get_all_guild_ids, get_server_data, get_youtube_settings, setup_database
from bs4 import BeautifulSoup
import re

# Load environment variables
load_dotenv()

# Initialize the database
init_db()
setup_database()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')

CHECK_INTERVAL = 60
TWITCH_API_URL = "https://api.twitch.tv/helix/streams"

notified_streams = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.error(f"Error fetching OAuth token: {e}")
        logger.error(f"Response content: {response.content.decode()}")
        raise
    return response.json()['access_token']

def check_stream_status(access_token, streamer):
    """Check if a Twitch stream is live."""
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {access_token}'
    }
    params = {'user_login': streamer}
    logger.info(f"Sending request to Twitch API for streamer: {streamer}")
    response = requests.get(TWITCH_API_URL, headers=headers, params=params)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error checking stream status for {streamer}: {e}")
        logger.error(f"Response content: {response.content.decode()}")
        return None
    data = response.json()
    logger.info(f"Received response from Twitch API for streamer {streamer}: {data}")
    if data['data']:
        logger.info(f"Streamer {streamer} is live")
        return {
            'title': data['data'][0]['title'],
            'category': data['data'][0]['game_name'],
            'url': f"https://www.twitch.tv/{streamer}"
        }
    logger.info(f"Streamer {streamer} is not live")
    return None

async def send_discord_message(channel_id, message, role_id=None):
    from bot import bot  # Import bot instance here to avoid circular import issues

    try:
        logger.info(f"Attempting to send message to channel ID {channel_id}")
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            logger.info(f"Channel not found in cache, attempting to fetch")
            try:
                channel = await bot.fetch_channel(int(channel_id))
            except Exception as e:
                logger.error(f"Error fetching channel: {e}")
                return

        if channel:
            if role_id:
                role_mention = f"<@&{role_id}>"
                message = f"{role_mention} {message}"

            logger.info(f"Sending message: {message[:50]}...")
            await channel.send(message)
            logger.info(f"Message sent successfully to channel ID {channel_id}")
        else:
            logger.error(f"Channel with ID {channel_id} not found. Ensure the bot has access to this channel.")
            logger.info(f"Bot is connected to the following guilds: {[guild.name for guild in bot.guilds]}")
            for guild in bot.guilds:
                logger.info(f"Guild: {guild.name} (ID: {guild.id})")
                for ch in guild.channels:
                    logger.info(f"Channel: {ch.name} (ID: {ch.id})")
    except Exception as e:
        logger.error(f"Error in send_discord_message: {e}")
    await asyncio.sleep(0)

def get_youtube_releases(channel_name):
    """Fetch new song releases from a YouTube channel's releases page."""
    url = f"https://www.youtube.com/@{channel_name}/releases"
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"Failed to fetch YouTube releases for channel {channel_name}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    releases = []

    # Find all video items
    video_items = soup.find_all('div', {'id': 'dismissible', 'class': 'style-scope ytd-grid-video-renderer'})

    for item in video_items:
        title_element = item.find('yt-formatted-string', {'id': 'video-title'})
        if title_element:
            title = title_element.text.strip()

            # Extract video ID from the href attribute
            video_id_match = re.search(r'href="/watch\?v=([^"]+)"', str(item))
            video_id = video_id_match.group(1) if video_id_match else None

            if video_id:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                releases.append({"title": title, "url": video_url})

    return releases

async def post_youtube_releases(channel_id, channel_name, role_id=None):
    """Post new YouTube releases to a Discord channel."""
    releases = get_youtube_releases(channel_name)
    if releases:
        message = f"🎵 New releases from @{channel_name} on YouTube:\n\n"
        for release in releases[:5]:  # Limit to 5 releases to avoid too long messages
            message += f"• {release['title']}\n{release['url']}\n\n"

        await send_discord_message(channel_id, message, role_id)
    else:
        logger.info(f"No new releases found for YouTube channel {channel_name}")
        
async def monitor_streams():
    global notified_streams
    access_token = get_oauth_token()
    logger.info("Starting monitor_streams function")
    while True:
        try:
            logger.info("Beginning stream check cycle")
            for guild_id in notified_streams.keys():
                streamers = get_streamers(guild_id)
                logger.info(f"Checking streamers for guild {guild_id}: {streamers}")
                for streamer in streamers:
                    logger.info(f"Checking status for streamer: {streamer}")
                    stream_info = check_stream_status(access_token, streamer)
                    if stream_info and streamer not in notified_streams[guild_id]:
                        logger.info(f"Streamer {streamer} is live. Attempting to send notification.")
                        server_data = get_server_data(guild_id)
                        channel_id = server_data.get('channel_id')
                        role_id = server_data.get('role_id')
                        if channel_id:
                            message = f"🔴 {streamer} is now live on Twitch!\n\nTitle: {stream_info['title']}\nPlaying: {stream_info['category']}\nhttps://twitch.tv/{streamer}"
                            logger.info(f"Sending message to channel {channel_id}: {message}")
                            await send_discord_message(channel_id, message, role_id)
                            notified_streams[guild_id].add(streamer)
                        else:
                            logger.warning(f"No channel_id found for guild {guild_id}")
                    elif not stream_info and streamer in notified_streams[guild_id]:
                        logger.info(f"Streamer {streamer} is no longer live. Removing from notified list.")
                        notified_streams[guild_id].remove(streamer)

                # Check YouTube releases
                server_data = get_server_data(guild_id)
                youtube_channel = server_data.get('youtube_channel')
                if youtube_channel:
                    youtube_channel_id, youtube_role_id = get_youtube_settings(guild_id)
                    if youtube_channel_id:
                        logger.info(f"Checking YouTube releases for channel: {youtube_channel}")
                        await post_youtube_releases(youtube_channel_id, youtube_channel, youtube_role_id)
                    else:
                        logger.warning(f"No YouTube channel ID set for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error in monitor_streams: {e}")

        logger.info(f"Stream check cycle complete. Sleeping for {CHECK_INTERVAL} seconds.")
        await asyncio.sleep(CHECK_INTERVAL)

def get_current_streamer(guild_id):
    streamers = get_streamers(guild_id)
    access_token = get_oauth_token()
    for streamer in streamers:
        stream_info = check_stream_status(access_token, streamer)
        if stream_info:
            logger.info(f"Current live streamer for guild {guild_id}: {streamer}")
            return streamer
    logger.info(f"No live streamers found for guild {guild_id}")
    return None

if __name__ == "__main__":
    # Initialize notified_streams for each guild
    guild_ids = get_all_guild_ids()  # Retrieve all guild IDs from the database
    for guild_id in guild_ids:
        notified_streams[guild_id] = set()

    # Start Twitch monitoring
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_streams())
    loop.run_forever()

