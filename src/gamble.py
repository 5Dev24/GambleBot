from typing import List
import commands
import discord
import data

class GambleBot(discord.Client):

	def __init__(self):
		super().__init__(intents = discord.Intents(messages = True, members = True, guilds = True))

		self.lockers = data.Locker()
		self.data = data.DataHandler(self)
		self.command_handler = commands.CommandHandler(self)

	async def on_ready(self):
		print(f"Readying as {self.user} ({self.user.id})")

		print(f"Use this link to join your bot to your server:\n\thttps://discord.com/api/oauth2/authorize?client_id={self.user.id}&permissions=8&scope=bot")

		await self.change_presence(activity = discord.Game("as the House"))

		guilds: List[discord.Guild] = self.guilds

		longest_name = max(guilds, key = lambda guild: guild.name.__len__()).name.__len__()
		most_members = max(guilds, key = lambda guild: guild.member_count).member_count.__str__().__len__()

		print("I'm in the following guilds:")
		for guild in guilds:
			invite = (await guild.invites())[:1]
			if invite.__len__(): invite = invite[0].url
			else: invite = "No invites"

			print(f'\t{guild.id}: "{guild.name:<{longest_name}}" ({guild.member_count:>{most_members}} member{"" if guild.member_count == 1 else "s"}): {invite}')

		if not guilds.__len__():
			print("\tNone ):")

		print("Readied")

	async def send_raw_message(self, triggered_by: discord.Message, text: str, prompt_user: bool = False) -> discord.Message:
		return await triggered_by.reply(text, mention_author = prompt_user)

	async def send_message(self, triggered_by: discord.Message, title: str, desc: str, color: discord.Colour, prompt_user: bool = False) -> discord.Message:
		return await triggered_by.reply(embed = discord.Embed(title = title, description = desc, color = color), mention_author = prompt_user)

	async def send_message_w_fields(self, triggered_by: discord.Message, title: str, desc: str, color: discord.Colour, *fields, prompt_user: bool = False) -> discord.Message:
		embed = discord.Embed(title = title, description = desc, color = color)

		i = 0
		end = fields.__len__()
		embed._fields = [] # Initialize to avoid AttributeError in ValueError and TypeError

		while i < end:
			if i + 1 >= end:
				raise ValueError(f"Missing name: str and value: str for field {embed._fields.__len__() + 1}")

			if not isinstance(fields[i], str):
				raise TypeError(f"The priovided name wasn't a string for field #{embed._fields.__len__() + 1}, it was a {fields[i].__class__.__name__}")

			if not isinstance(fields[i + 1], str):
				raise TypeError(f"The priovided value wasn't a string for field #{embed._fields.__len__() + 1}, it was a {fields[i + 1].__class__.__name__}")

			inline = i + 2 < end and isinstance(fields[i + 2], bool) and fields[i + 2]

			embed.add_field(name = fields[i], value = fields[i + 1], inline = inline)

			i += 3 if inline else 2

		return await triggered_by.reply(embed = embed, mention_author = prompt_user)

	async def on_message(self, message: discord.Message):
		content: List[str] = message.content.split(" ")

		cmd = content[0].lower()
		args = content[1:]

		guild_data: data.GuildDataType = data._default_guild_data() if message.guild is None else self.data.read_guild(message.guild.id)

		if guild_data["cmd_channel"] != -1 and guild_data["cmd_channel"] != message.channel.id:
			return # Not correct channel

		if not cmd.startswith(guild_data["cmd_prefix"]):
			return # Not command

		cmd = cmd[guild_data["cmd_prefix"].__len__():]

		if not cmd.__len__():
			return # Empty command

		await self.command_handler.receive(cmd, args, message, message.author, message.guild)