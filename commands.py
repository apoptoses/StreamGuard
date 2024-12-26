import discord
from discord.ext import commands
from storage import get_server_data, set_server_data, add_streamer, remove_streamer, get_streamers, get_youtubers, add_youtuber, remove_youtuber


class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_guild_data(self, guild_id):
        guild_data = get_server_data(guild_id)
        self.twitch_role_id = guild_data.get('role_id', 0)
        self.twitch_channel_id = guild_data.get('channel_id', 0)
        self.youtube_role_id = guild_data.get('youtube_role_id', 0)
        self.youtube_channel_id = guild_data.get('youtube_channel_id', 0)


    @commands.command(name="help")
    async def help(self, ctx, command_name: str = None):
        try:
            if command_name is None:
                # general help message
                print("Help command invoked")
                embed = discord.Embed(title="StreamGuard's Discord Bot Commands", description="Use the `!` prefix to execute these commands.", color=0x738bd7)
                embed.add_field(name="help", value="Displays this message, but can be used to get a description for a single command. Usage: `!help [command_name]`", inline=False)
                embed.add_field(name="ping", value="Check the bot's latency. Usage: `!ping`", inline=False)
                embed.add_field(name="set", value="Set the role or channel ID for Twitch or YouTube. Usage: `!set <role|channel> <id> [twitch|youtube]`", inline=False)
                embed.add_field(name="remove", value="Remove the role or channel ID. Usage: `!remove <role|channel>`", inline=False)
                embed.add_field(name="list", value="List the current role and channel IDs. Usage: `!list`", inline=False)
                embed.add_field(name="purge", value="Delete a specified number of messages. Usage: `!purge <amount>`", inline=False)
                embed.add_field(name="streamers", value="Customizable notifier for Twitch streams. Usage: `!streamers <add>, <remove>, or <list>`", inline=False)
                embed.add_field(name="youtubers", value="Customizable notifier for YouTube releases. Usage: `!youtubers <add>, <remove>, or <list>`", inline=False)
                await ctx.send(embed=embed)
            else:
                # specific command help
                command = self.bot.get_command(command_name)
                if command and command.name != "help":  # exclude the help command itself
                    descriptions = {
                        "ping": "Simply type `!ping` to see the response time.",
                        "set": "Use it like this: `!set <role|channel> <id> [twitch|youtube]`. Replace `<role|channel>` with either 'role' or 'channel', `<id>` with the actual ID you want to set, and optionally specify 'twitch' or 'youtube' (defaults to twitch if not specified). To get IDs, go to Advanced settings and turn on Developer Mode. Then right-click the role or channel and select 'Copy ID'.",
                        "remove": "Use it like this: `!remove <role|channel>`. Replace `<role|channel>` with either 'role' or 'channel' to remove the corresponding ID.",
                        "list": "Just type `!list` to see the current information of role ID and channel ID.",
                        "purge": "Use it like this: `!purge <amount>`. Replace `<amount>` with the number of messages you want to delete.",
                        "streamers": "Use it like this: `!streamers <add>, <remove>, or <list>`. Replace `<add>` with the Twitch streamer's name you want to add, `<remove>` with the Twitch streamer's name you want to remove, or `<list>` to see the current list of streamers.",
                        "youtubers": "Use it like this: `!youtubers <add>, <remove>, or <list>`. Replace `<add>` with the YouTube channel's name you want to add, '<remove>` with the YouTube channel's name you want to remove, or `<list>` to see the current list of YouTube channels."
                    }
                    description = descriptions.get(command_name, "No detailed description available.")
                    embed = discord.Embed(title=f"Help for `{command_name}`", description=description, color=0x738bd7)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"❌ Command `{command_name}` not found.")
        except Exception as e:
            print(f"Error in help command: {e}")

    @commands.command(name="ping", help="Checks the bot's latency.")
    async def ping(self, ctx):
        try:
            print("Ping command invoked")
            latency = round(self.bot.latency * 1000)
            await ctx.send(f"Pong! Latency: {latency}ms")
        except Exception as e:
            print(f"Error in ping command: {e}")
    
    @commands.command(name="set", help="Set role or channel for Twitch or YouTube notifications. Usage: !set [role|channel] [ID] [twitch|youtube]")
    @commands.has_permissions(manage_channels=True)
    async def set(self, ctx, setting_type: str, id: int, platform: str = "twitch"):
        try:
            if setting_type not in ["role", "channel"]:
                await ctx.send("❌ Invalid setting type. Use 'role' or 'channel'.")
                return

            if platform not in ["twitch", "youtube"]:
                await ctx.send("❌ Invalid platform. Use 'twitch' or 'youtube'.")
                return

            guild_id = ctx.guild.id
            server_data = get_server_data(guild_id)

            if platform == "twitch":
                if setting_type == "role":
                    server_data['role_id'] = id
                else:  # channel
                    server_data['channel_id'] = id
            else:  # youtube
                if setting_type == "role":
                    server_data['youtube_role_id'] = id
                else:  # channel
                    server_data['youtube_channel_id'] = id

            set_server_data(guild_id, **server_data)

            await ctx.send(f"✅ {setting_type.capitalize()} ID for {platform.capitalize()} has been set to {id}.")
        except Exception as e:
            print(f"Error in set command: {e}")
            await ctx.send("❌ An error occurred while updating settings.")
    
    @commands.command(name="remove", help="Removes the bot's role or channel ID.")
    async def remove(self, ctx, setting_type: str):
        try:
            self.load_guild_data(ctx.guild.id)
            setting_type = setting_type.lower()
        
            if setting_type not in ["role", "channel"]:
                await ctx.send("❌ Invalid setting type. Use either 'role' or 'channel'.")
                return
        
            if setting_type == "role":
                self.role_id = 0
                set_server_data(ctx.guild.id, role_id=self.role_id)
                await ctx.send("✅ Role removed.")
            else:
                self.channel_id = 0
                set_server_data(ctx.guild.id, channel_id=self.channel_id)
                await ctx.send("✅ Channel removed.")
        except Exception as e:
            print(f"Error in remove command: {e}")
        
    @commands.command(name="list", help="Lists the current role and channel IDs for Twitch and YouTube.")
    async def list_ids(self, ctx):
        try:
            self.load_guild_data(ctx.guild.id)
            
            # Twitch settings
            twitch_role = ctx.guild.get_role(self.twitch_role_id)
            twitch_channel = self.bot.get_channel(self.twitch_channel_id)
            twitch_role_info = f"Twitch Role: `{twitch_role.name}` (ID: `{self.twitch_role_id}`)" if twitch_role else f"Twitch Role: `None` (ID: `{self.twitch_role_id}`)"
            twitch_channel_info = f"Twitch Channel: `{twitch_channel.name}` (ID: `{self.twitch_channel_id}`)" if twitch_channel else f"Twitch Channel: `None` (ID: `{self.twitch_channel_id}`)"

            # YouTube settings
            youtube_role = ctx.guild.get_role(self.youtube_role_id)
            youtube_channel = self.bot.get_channel(self.youtube_channel_id)
            youtube_role_info = f"YouTube Role: `{youtube_role.name}` (ID: `{self.youtube_role_id}`)" if youtube_role else f"YouTube Role: `None` (ID: `{self.youtube_role_id}`)"
            youtube_channel_info = f"YouTube Channel: `{youtube_channel.name}` (ID: `{self.youtube_channel_id}`)" if youtube_channel else f"YouTube Channel: `None` (ID: `{self.youtube_channel_id}`)"

            await ctx.send(f"**Current Settings**\n\n**Twitch:**\n{twitch_role_info}\n{twitch_channel_info}\n\n**YouTube:**\n{youtube_role_info}\n{youtube_channel_info}")
        except Exception as e:
            print(f"Error in list_ids command: {e}")
            await ctx.send("An error occurred while fetching the settings. Please try again later.")
            
    @commands.command(name="purge", help="Deletes a specified number of messages from the channel.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = None):
        try:
            if amount is None or amount < 1:
                await ctx.send("❌ You must specify a positive number of messages to delete.")
                return
            deleted = await ctx.channel.purge(limit=amount)
            await ctx.send(f"✅ Deleted {len(deleted)} message(s).", delete_after=5)
        except Exception as e:
            print(f"Error in purge command: {e}")
    
    @commands.command(name="streamers", help="Add, remove, or list Twitch streamers in the monitoring list.")
    async def streamers(self, ctx, action: str = None, streamer_name: str = None):
        try:
            guild_id = ctx.guild.id
        
            if action is None:
                await ctx.send("❌ Please specify an action: add, remove, or list.")
                return

            action = action.lower()

            if action == "list":
                streamers = get_streamers(guild_id)
                if streamers:
                    await ctx.send(f"📋 Current Twitch streamers: {', '.join(streamers)}")
                else:
                    await ctx.send("📋 No Twitch streamers in the list.")
            elif action == "add":
                if streamer_name:
                    add_streamer(guild_id, streamer_name)
                    await ctx.send(f"✅ Added Twitch streamer: {streamer_name}")
                else:
                    await ctx.send("❌ Please provide a Twitch streamer name to add.")
            elif action == "remove":
                if streamer_name:
                    remove_streamer(guild_id, streamer_name)
                    await ctx.send(f"✅ Removed Twitch streamer: {streamer_name}")
                else:
                    await ctx.send("❌ Please provide a Twitch streamer name to remove.")
            else:
                await ctx.send("❌ Invalid action. Use 'add', 'remove', or 'list'.")
        except Exception as e:
            print(f"Error in streamers command: {e}")
            await ctx.send("An error occurred while managing streamers. Please try again later.")

    @commands.command(name="youtubers", help="Add, remove, or list YouTube channels in the monitoring list.")
    async def youtubers(self, ctx, action: str = None, channel_name: str = None):
        try:
            if action is None:
                await ctx.send("❌ Please specify an action: add, remove, or list.")
                return

            action = action.lower()

            if action == "list":
                youtubers = get_youtubers(ctx.guild.id)
                if youtubers:
                    await ctx.send(f"📺 Monitored YouTube channels:\n{', '.join(youtubers)}")
                else:
                    await ctx.send("No YouTube channels are currently being monitored.")
            elif action in ["add", "remove"]:
                if channel_name is None:
                    await ctx.send(f"❌ Please provide a YouTube channel name to {action}.")
                    return

                if action == "add":
                    add_youtuber(ctx.guild.id, channel_name)
                    await ctx.send(f"✅ Added YouTube channel '{channel_name}' to the monitoring list.")
                else:  # remove
                    if remove_youtuber(ctx.guild.id, channel_name):
                        await ctx.send(f"✅ Removed YouTube channel '{channel_name}' from the monitoring list.")
                    else:
                        await ctx.send(f"❌ YouTube channel '{channel_name}' was not in the monitoring list.")
            else:
                await ctx.send("❌ Invalid action. Use 'add', 'remove', or 'list'.")
        except Exception as e:
            print(f"Error in youtubers command: {e}")
            await ctx.send("An error occurred while processing the command.")
