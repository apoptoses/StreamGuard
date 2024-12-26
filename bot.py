import sys
import os
import threading
import random
import logging
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtCore import QObject, pyqtSignal
from gui import StreamGuardGUI
from flask import Flask
from app import get_current_streamer
from storage import get_server_data, set_server_data, get_streamers, get_all_guild_ids

class BotSignals(QObject):
    update_servers = pyqtSignal()

bot_signals = BotSignals()

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Discord bot
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize Flask app
flask_app = Flask(__name__)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    update_status.start()
    heartbeat.start()
    if hasattr(bot, 'gui'):
        bot_signals.update_servers.emit()
        
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.TextChannel):
        guild_name = message.guild.name
        guild_id = message.guild.id
        member = message.author

        if member.guild_permissions.administrator:
            permission_type = "Administrator"
        elif member.guild_permissions.manage_messages:
            permission_type = "Manage Messages"
        else:
            permission_type = "Regular User"

        print(f"Server Message: {message.content} | Server Name: {guild_name} (ID: {guild_id}) | User: {message.author} | Permissions: {permission_type}")

        target_guild_id = 1295227199418269777
        category_id = 1318845660891451392

        target_guild = bot.get_guild(target_guild_id)
        if target_guild is None:
            print(f"[ ERROR ] Target guild with ID {target_guild_id} not found.")
            return

        category = discord.utils.get(target_guild.categories, id=category_id)
        if category is None:
            print(f"[ ERROR ] Category with ID {category_id} not found in target guild {target_guild.name} (ID: {target_guild.id})")
            return

        server_data = get_server_data(message.guild.id)
        log_channel_id = server_data.get('log_channel_id')

        log_channel = None
        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)

        if not log_channel:
            log_channel_name = f"log-{message.guild.name.lower().replace(' ', '-')}"
            log_channel = discord.utils.get(target_guild.text_channels, name=log_channel_name)

            if not log_channel:
                try:
                    log_channel = await target_guild.create_text_channel(log_channel_name, category=category)
                    print(f"[ INFO ] Created new log channel: {log_channel.name} in target guild {target_guild.name} (ID: {target_guild.id})")
                except Exception as e:
                    print(f"[ ERROR ] Failed to create log channel: {e}")
                    return

            set_server_data(message.guild.id, log_channel_id=log_channel.id)

        try:
            embed = discord.Embed(
                title="💬 Server Message",
                description=message.content,
                color=discord.Color(random.randint(0, 0xFFFFFF))
            )
            embed.set_author(name=str(message.author), icon_url=message.author.avatar.url if message.author.avatar else None)
            embed.add_field(name="User", value=str(message.author), inline=True)
            embed.add_field(name="Permissions", value=permission_type, inline=True)
            embed.add_field(name="Channel", value=message.channel.name, inline=True)
            embed.set_footer(text=f"Message sent at {message.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")

            await log_channel.send(embed=embed)
        except Exception as e:
            print(f"[ ERROR ] Failed to send message to log channel: {e}")

    else:
        print(f"Direct Message: {message.content} | From User: {message.author}")

        target_guild_id = 1295227199418269777
        log_channel_id = 1318850799987593267

        target_guild = bot.get_guild(target_guild_id)
        if target_guild:
            log_channel = target_guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    embed = discord.Embed(
                        title="📩 Direct Message",
                        description=message.content,
                        color=discord.Color(random.randint(0, 0xFFFFFF))
                    )
                    embed.set_author(name=str(message.author), icon_url=message.author.avatar.url if message.author.avatar else None)
                    embed.set_footer(text=f"Message sent at {message.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")

                    await log_channel.send(embed=embed)
                except Exception as e:
                    print(f"[ ERROR ] Failed to send direct message to log channel: {e}")
            else:
                print(f"[ ERROR ] Log channel with ID {log_channel_id} not found in target guild.")
        else:
            print(f"[ ERROR ] Target guild with ID {target_guild_id} not found.")

    await bot.process_commands(message)

@bot.event
async def on_guild_update(before, after):
    if before.name != after.name:
        pass

@tasks.loop(minutes=1)
async def update_status():
    try:
        for guild in bot.guilds:
            streamer = get_current_streamer(guild.id)
            if streamer:
                activity = discord.Activity(name=f"{streamer} on Twitch", type=discord.ActivityType.watching)
                await bot.change_presence(activity=activity, status=discord.Status.online)
                logger.info(f"Updated bot status: Watching {streamer} on Twitch")
                return  # Exit after finding the first live streamer

        # If no streamers are live, set a default status
        await bot.change_presence(activity=discord.Activity(name="You", type=discord.ActivityType.watching))
        logger.info("Updated bot status: Watching You")
    except Exception as e:
        logger.error(f"Error updating bot status: {e}")

def get_all_streamers():
    all_streamers = set()
    guild_ids = []
    for guild in bot.guilds:
        all_streamers.update(get_streamers(guild.id))
        guild_ids.append(guild.id)
    return list(all_streamers), guild_ids

def get_server_names():
    return {guild.id: guild.name for guild in bot.guilds}

def run_flask_app():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

@tasks.loop(minutes=1)
async def heartbeat():
    print("[ INFO ] Bot is still running.")

def run_bot():
    bot.run(DISCORD_BOT_TOKEN)

def main():
    app = QApplication(sys.argv)

    main_window = StreamGuardGUI()
    main_window.set_get_all_streamers_func(get_all_streamers)
    main_window.set_get_server_names_func(get_server_names)
    
    # Connect the signal to the GUI method
    bot_signals.update_servers.connect(main_window.update_servers_list)
    
    # Pass the GUI instance to the bot
    bot.gui = main_window

    # Start the Discord bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # Show the GUI
    main_window.show()

    # Set up a timer to keep the GUI responsive
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)

    # Start the GUI event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()