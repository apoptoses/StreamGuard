import discord
from discord.ext import commands
from storage import get_server_data, set_server_data, add_streamer, remove_streamer, get_streamers

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_id = 0
        self.channel_id = 0

    def load_guild_data(self, guild_id):
        guild_data = get_server_data(guild_id)
        self.role_id = guild_data.get('role_id', 0)
        self.channel_id = guild_data.get('channel_id', 0)


    @commands.command(name="help")
    async def help(self, ctx, command_name: str = None):
        try:
            if command_name is None:
                # general help message
                print("Help command invoked")
                embed = discord.Embed(title="StreamGuard's Discord Bot Commands", description="Use the `!` prefix to execute these commands.", color=0x738bd7)
                embed.add_field(name="ping", value="Check the bot's latency. Usage: `!ping`", inline=False)
                embed.add_field(name="set_role", value="Set the role ID to ping when streamer is live . Usage: `!set_role <role_id>`", inline=False)
                embed.add_field(name="set_channel", value="Set the channel ID to post in when streamer is live. Usage: `!set_channel <channel_id>`", inline=False)
                embed.add_field(name="list", value="List the current role and channel IDs. Usage: `!list`", inline=False)
                embed.add_field(name="purge", value="Delete a specified number of messages. Usage: `!purge <amount>`", inline=False)
                embed.add_field(name="streamers", value="Customizable notifier for Twitch streams. Usage: `!streamers <add>, <remove>, or <list>`", inline=False)
                await ctx.send(embed=embed)
            else:
                # specific command help
                command = self.bot.get_command(command_name)
                if command and command.name != "help":  # exclude the help command itself
                    descriptions = {
                        "ping": "Simply type `!ping` to see the response time.",
                        "set_role": "Use it like this: `!set_role <role_id>`. Replace `<role_id>` with the actual ID of the role you want to set. To get the role ID head to Advanced settings and turn on Developer Mode. Then right click the role you want use and click Copy Role ID.",
                        "set_channel": "Use it like this: `!set_channel <channel_id>`. Replace `<channel_id>` with the actual ID of the channel you want to set. To get the channel ID head to Advanced settings and turn on Developer Mode. Then right click the channel you want use and click Copy Channel ID.",
                        "list": "Just type `!list` to see the current information of role ID and channel ID.",
                        "purge": "Use it like this: `!purge <amount>`. Replace `<amount>` with the number of messages you want to delete.",
                        "streamers": "Use it like this: `!streamers <add>, <remove>, or <list>`. Replace `<add>` with the Twitch streamer's name you want to add, `<remove>` with the Twitch streamer's name you want to remove, or `<list>` to see the current list of streamers."
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
            
    @commands.command(name="set_role", help="Updates the bot's role ID. Provide the role's ID.")
    async def set_role(self, ctx, new_role_id: int):
        try:
            self.load_guild_data(ctx.guild.id)
            self.role_id = new_role_id
            set_server_data(ctx.guild.id, role_id=self.role_id)
            role = ctx.guild.get_role(self.role_id)
            if role:
                await ctx.send(f"✅ Role updated to: `{role.name}` (ID: `{self.role_id}`)")
            else:
                await ctx.send(f"❌ Role with ID `{self.role_id}` not found.")
        except Exception as e:
            print(f"Error in set_role command: {e}")

    @commands.command(name="set_channel", help="Updates the bot's channel ID. Provide the channel's ID.")
    async def set_channel(self, ctx, new_channel_id: int = None):
        try:
            self.load_guild_data(ctx.guild.id)
            if not new_channel_id:
                await ctx.send("❌ You must provide a valid channel ID.")
                return
            self.channel_id = new_channel_id
            set_server_data(ctx.guild.id, channel_id=self.channel_id)
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                await ctx.send(f"✅ Channel updated to: `{channel.name}` (ID: `{self.channel_id}`)")
            else:
                await ctx.send(f"❌ Channel with ID `{self.channel_id}` not found.")
        except Exception as e:
            print(f"Error in set_channel command: {e}")

    @commands.command(name="list", help="Lists the current role and channel IDs.")
    async def list_ids(self, ctx):
        try:
            self.load_guild_data(ctx.guild.id)
            role = ctx.guild.get_role(self.role_id)
            channel = self.bot.get_channel(self.channel_id)
            role_info = f"Role: `{role.name}` (ID: `{self.role_id}`)" if role else f"Role: `None` (ID: `{self.role_id}`)"
            channel_info = f"Channel: `{channel.name}` (ID: `{self.channel_id}`)" if channel else f"Channel: `None` (ID: `{self.channel_id}`)"
            await ctx.send(f"**Current Settings**\n{role_info}\n{channel_info}")
        except Exception as e:
            print(f"Error in list_ids command: {e}")
            
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
    
    @commands.command(name="streamers", help="Add, remove, or list streamers in the monitoring list.")
    async def streamers(self, ctx, action: str = None, streamer_name: str = None):
        try:
            guild_id = ctx.guild.id 
            if action is None:
                await ctx.send("❌ You must specify an action: `add`, `remove`, or `list`.")
                return
            if action.lower() == "add" and streamer_name:
                add_streamer(guild_id, streamer_name)
                await ctx.send(f"✅ Added `{streamer_name}` to the monitoring list.")
            elif action.lower() == "remove" and streamer_name:
                remove_streamer(guild_id, streamer_name)
                await ctx.send(f"✅ Removed `{streamer_name}` from the monitoring list.")
            elif action.lower() == "list":
                streamers = get_streamers(guild_id)
                if streamers:
                    streamer_list = "\n".join(streamers)
                    await ctx.send(f"**Current Streamers in Monitoring List:**\n{streamer_list}")
                else:
                    await ctx.send("❌ The monitoring list is currently empty.")
            else:
                await ctx.send("❌ Invalid action or missing streamer name. Use `add`, `remove`, or `list`.")
        except Exception as e:
            print(f"Error in streamers command: {e}")

    

