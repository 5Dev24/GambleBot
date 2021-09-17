from typing import TypedDict, Optional, Tuple, Dict, List
import datetime
import discord
import asyncio
import random
import gamble
import random
import time

class Command:

	def __init__(self, parent: "gamble.GambleBot"):
		self.parent = parent

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild] = None) -> None:
		raise NotImplementedError()

	def __args__(self) -> str:
		return "" # Default no args message

	def __help__(self) -> str:
		return "Help message not implemented yet"

class Bal(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild]) -> None:
		if args.__len__():
			user_id = args[0]
			if user_id.startswith("<@") and user_id.endswith(">"):
				user_id = user_id[2:-1]
				if user_id.startswith("!"):
					user_id = user_id[1:]

				try:
					user_id	= int(user_id)

					if user_id == author.id:
						bal = self.parent.data.read_user(author.id)["bal"]
						await self.parent.send_message(message, "Your balance is", f"{bal} credit{'' if bal == 1 else 's'}", discord.Color.gold())
						return

					bal = self.parent.data.read_user(user_id)['bal']
					await self.parent.send_message(message, "Their balance is", f"{bal} credit{'' if bal == 1 else 's'}", discord.Color.gold())
					return

				except ValueError:
					await self.parent.send_message_w_fields(message, "Invalid user", "Use bal [@user]", discord.Color.red(), "Invalid argument @user", "Try mentioning a user")
					return

			await self.parent.send_message_w_fields(message, "Invalid user", "Use bal [@user]", discord.Color.red(), "Invalid argument @user", "Try mentioning a user")
			return

		bal = self.parent.data.read_user(author.id)["bal"]
		await self.parent.send_message(message, "Your balance is", f"{bal} credit{'' if bal == 1 else 's'}", discord.Color.gold())

	def __args__(self) -> str:
		return "[@user]"

	def __help__(self) -> str:
		return "Check your balance"

class Roll(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild]) -> None:
		with self.parent.user_locker.lock(author.id):
			user_data = self.parent.data.read_user(author.id)
			now = int(time.time())

			if user_data["roll"] + 7200 <= now:
				dies = [
					random.randint(1, 6)
					for _ in range(3)
				]

				total = sum(dies)
				gain = total * 10

				await self.parent.send_message_w_fields(message, f"You rolled a total of {total}", f"Giving you {gain} credits", discord.Color.gold(),
				*[
					f(i)
					for i in range(dies.__len__())
						for f in
						(
							lambda x: f"You rolled a {dies[x]} on die #{x + 1}",
							lambda x: f"Making you {dies[x] * 10} credits"
						) # Don't look
				])

				user_data["bal"] += gain
				user_data["roll"] = now
				if not self.parent.data.modify_user(author.id, user_data):
					await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)

			else:
				await self.parent.send_message(message, "You're last roll was too recent", f"Try again in {datetime.timedelta(seconds = user_data['roll'] + 7200 - now)}", discord.Color.red())

	def __help__(self) -> str:
		return "Roll 3 dies every 2 hours for credits"

class Daily(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild]) -> None:
		with self.parent.user_locker.lock(author.id):
			user_data = self.parent.data.read_user(author.id)
			today = datetime.datetime.now().strftime("%Y%m%d")

			if today == user_data["daily"]:
				await self.parent.send_message(message, "You've already claimed you daily", "Try again tomorrow", discord.Color.red())
			else:
				user_data["bal"] += 1000
				user_data["daily"] = today
				await self.parent.send_message(message, "Take your daily credits!", f"You now have {user_data['bal']} credits", discord.Color.gold())

				if not self.parent.data.modify_user(author.id, user_data):
					await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)

	def __help__(self) -> str:
		return "Collect 1000 tokens daily"

class Help(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild]) -> None:
		await self.parent.send_message_w_fields(message, "Help", "Below is a list of all commands and their help messages", discord.Color.gold(), *self.parent.command_handler._help_fields)

	def __help__(self) -> str:
		return "See all help messages"

class SlotElement(TypedDict):
	emote: str
	chance: float
	multiplier: float

class SlotsManager:

	def __init__(self):
		self.apple: SlotElement       = {"emote": "apple",       "chance": .70,  "multiplier": 0.5 }
		self.green_apple: SlotElement = {"emote": "green_apple", "chance": .60,  "multiplier": 0.75}
		self.tangerine: SlotElement   = {"emote": "tangerine",   "chance": .50,  "multiplier": 1   }
		self.pear: SlotElement        = {"emote": "pear",        "chance": .45,  "multiplier": 1.25}
		self.lemon: SlotElement       = {"emote": "lemon",       "chance": .35,  "multiplier": 1.75}
		self.melon: SlotElement       = {"emote": "melon",       "chance": .30,  "multiplier": 2.5 }
		self.strawberry: SlotElement  = {"emote": "strawberry",  "chance": .20,  "multiplier": 3   }
		self.peach: SlotElement       = {"emote": "peach",       "chance": .15,  "multiplier": 4   }
		self.kiwi: SlotElement        = {"emote": "kiwi",        "chance": .10,  "multiplier": 4.5 }
		self.blueberry: SlotElement   = {"emote": "blueberries", "chance": .10,  "multiplier": 5   }
		self.grapes: SlotElement      = {"emote": "grapes",      "chance": .05,  "multiplier": 8   }
		self.cherry: SlotElement      = {"emote": "cherries",    "chance": .025, "multiplier": 10  }

		self.slots: Tuple[SlotElement] = (
			self.apple,
			self.green_apple,
			self.tangerine,
			self.pear,
			self.lemon,
			self.melon,
			self.strawberry,
			self.peach,
			self.kiwi,
			self.blueberry,
			self.grapes,
			self.cherry
		)

		total_chance = sum([slot["chance"] for slot in self.slots])
		for slot in self.slots:
			slot["chance"] = slot["chance"] / total_chance

		self.weights = tuple([slot["chance"] for slot in self.slots])

	def random_slot(self):
		return random.choices(self.slots, self.weights)[0]

class SlotMachine:

	def __init__(self, parent: "gamble.GambleBot", bet: int, rows: int = 10):
		self.parent = parent
		self.slots: List[List[SlotElement]] = []
		self.slot_message: discord.Message = None
		self.win = random.random() < .6 # 60% chance to win
		self.bet = bet

		rows = rows if 3 <= rows <= 15 else 10
		for row in range(rows):
			if self.win and row == rows - 2:
				self.slots.append([parent.command_handler.slots_manager.random_slot()] * 3)
				continue

			slots = [parent.command_handler.slots_manager.random_slot(), parent.command_handler.slots_manager.random_slot(), parent.command_handler.slots_manager.random_slot()]

			while slots[0]["emote"] == slots[1]["emote"] == slots[2]["emote"]:
				slots = [parent.command_handler.slots_manager.random_slot(), parent.command_handler.slots_manager.random_slot(), parent.command_handler.slots_manager.random_slot()]

			self.slots.append(slots)

	def new_row(self):
		for i in range(self.slots.__len__() - 1):
			self.slots[i] = self.slots[i + 1]

		del self.slots[i + 1]

	async def payout(self, message: discord.Message, author: discord.User):
		if self.slots[1][0]["emote"] == self.slots[1][1]["emote"] == self.slots[1][2]["emote"]:
			win_amount = int(self.bet * (1 + self.slots[1][0]["multiplier"]))

			await self.slot_message.edit(content = None, embed = discord.Embed(title = "Slot Machine", description = 
				f'**=** :{self.slots[1][0]["emote"]}: :{self.slots[1][1]["emote"]}: :{self.slots[1][2]["emote"]}: **=**', color = discord.Color.gold())
				.add_field(name = "You won!", value = f"You got {win_amount} credit{'' if win_amount == 1 else 's'}"),
				allowed_mentions = self.parent.command_handler.mentions)

			with self.parent.user_locker.lock(author.id): # Prevent balance from being overritten
				user_data = self.parent.data.read_user(author.id)
				user_data["bal"] += win_amount
				if not self.parent.data.modify_user(author.id, user_data):
					await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)
			return

		await self.slot_message.edit(content = None, embed = discord.Embed(title = "Slot Machine", description =
			f'= :{self.slots[1][0]["emote"]}: :{self.slots[1][1]["emote"]}: :{self.slots[1][2]["emote"]}: =',
			color = discord.Color.gold()), allowed_mentions = self.parent.command_handler.mentions)

	async def roll(self, message: discord.Message):
		async def do_a_barrel_roll():
			await asyncio.sleep(1)
			self.new_row()
			await self.slot_message.edit(content = self.__str__(), allowed_mentions = self.parent.command_handler.mentions)

		self.slot_message = await self.parent.send_raw_message(message, self.__str__())
		for _ in range(self.slots.__len__() - 3):
			await do_a_barrel_roll()

		await asyncio.sleep(1)

	def __str__(self) -> str:
		return f'''** **   :{self.slots[2][0]["emote"]}: :{self.slots[2][1]["emote"]}: :{self.slots[2][2]["emote"]}:
{"**=**" if self.win else "="} :{self.slots[1][0]["emote"]}: :{self.slots[1][1]["emote"]}: :{self.slots[1][2]["emote"]}: {"**=**" if self.win else "="}
    :{self.slots[0][0]["emote"]}: :{self.slots[0][1]["emote"]}: :{self.slots[0][2]["emote"]}:'''

class Slots(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild]) -> None:
		if args.__len__():
			bet = args[0]

			try:
				bet = int(bet)

			except ValueError:
				return await self.parent.send_message_w_fields(message, "Invalid bet", "Use slots <bet>", discord.Color.red(), "Invalid argument bet", "Try specifying a positive integer")

			if bet < 0:
				return await self.parent.send_message_w_fields(message, "Invalid bet", "Use slots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be positive")

			if bet < 20:
				return await self.parent.send_message_w_fields(message, "Invalid bet", "Use slots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be at least 20 credits")

			if bet > 2500:
				return await self.parent.send_message_w_fields(message, "Invalid bet", "Use slots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet cannot be greater than 2500 credits")

			with self.parent.user_locker.lock(author.id): # When doing a balance check, we need to lock user data to prevent a negative balance
				user_data = self.parent.data.read_user(author.id)

				if user_data["bal"] < bet:
					return await self.parent.send_message_w_fields(message, "Invalid bet", "Use slots <bet>", discord.Color.red(), "Invalid argument bet", "You don't have enough credits to make that bet")

				user_data["bal"] -= bet
				if not self.parent.data.modify_user(author.id, user_data):
					return await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)

				machine = SlotMachine(self.parent, bet)
				await machine.roll(message)
				return await machine.payout(message, author)

		await self.parent.send_message_w_fields(message, "Invalid usage", "Use slots <bet>", discord.Color.red(), "Missing argument", "You need to specify a bet")

	def __args__(self) -> str:
		return "<bet>"

	def __help__(self) -> str:
		return "Spin the wheel"

class FastSlots(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild]) -> None:
		if args.__len__():
			bet = args[0]

			try:
				bet = int(bet)

			except ValueError:
				return await self.parent.send_message_w_fields(message, "Invalid bet", "Use fslots <bet>", discord.Color.red(), "Invalid argument bet", "Try specifying a positive whole number")

			if bet < 0:
				return await self.parent.send_message_w_fields(message, "Invalid bet", "Use fslots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be positive")

			if bet < 20:
				return await self.parent.send_message_w_fields(message, "Invalid bet", "Use fslots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be at least 20 credits")

			if bet > 2500:
				return await self.parent.send_message_w_fields(message, "Invalid bet", "Use fslots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet cannot be greater than 2500 credits")

			with self.parent.user_locker.lock(author.id): # When doing a balance check, we need to lock user data to prevent a negative balance
				user_data = self.parent.data.read_user(author.id)

				if user_data["bal"] < bet:
					return await self.parent.send_message_w_fields(message, "Invalid bet", "Use fslots <bet>", discord.Color.red(), "Invalid argument bet", "You don't have enough credits to make that bet")

				user_data["bal"] -= bet
				if not self.parent.data.modify_user(author.id, user_data):
					return await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)

				machine = SlotMachine(self.parent, bet, 3)
				await machine.roll(message)
				return await machine.payout(message, author)

		await self.parent.send_message_w_fields(message, "Invalid usage", "Use fslots <bet>", discord.Color.red(), "Missing argument", "You need to specify a bet")

	def __args__(self) -> str:
		return "<bet>"

	def __help__(self) -> str:
		return "Spin the wheel quickly"

class Pay(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild] = None) -> None:
		if args.__len__() < 2:
			return await self.parent.send_message_w_fields(message, "Invalid usage", "Use pay <@user> <amount>", discord.Color.red(), f"Missing argument{'' if args.__len__() == 1 else 's'}", "You need to specify the recipient and the amount of credits to send")

		amount_to_pay = args[1]

		try:
			amount_to_pay = int(amount_to_pay)
		except ValueError:
			return await self.parent.send_message_w_fields(message, "Invalid amount", "Use pay <@user> <amount>", discord.Color.red(), "Invalid argument amount", "Try specifying a positive whole number")

		if amount_to_pay <= 0:
			return await self.parent.send_message_w_fields(message, "Invalid amount", "Use pay <@user> <amount>", discord.Color.red(), "Invalid argument amount", "The amount must be positive and not zero")

		with self.parent.user_locker.lock(author.id): # Because we're checking the balance, we need to lock data after we check as two payments close to each other can both pass this check and lead to a negative balance
			sender_data = self.parent.data.read_user(author.id)

			if sender_data["bal"] < amount_to_pay:
				return await self.parent.send_message_w_fields(message, "Invalid amount", "Use pay <@user> <amount>", discord.Color.red(), "Invalid argument amount", f"You don't have enought credits to send {amount_to_pay}")

			recipient_id = args[0]
			if recipient_id.startswith("<@") and recipient_id.endswith(">"):
				recipient_id = recipient_id[2:-1]
				if recipient_id.startswith("!"):
					recipient_id = recipient_id[1:]

				try:
					recipient_id = int(recipient_id)

					if recipient_id == author.id:
						return await self.parent.send_message(message, "What?", "You can't pay yourself", discord.Color.red())

					with self.parent.user_locker.lock(recipient_id):
						recipient_data = self.parent.data.read_user(recipient_id)

						sender_data["bal"] -= amount_to_pay
						recipient_data["bal"] += amount_to_pay

						flag1 = self.parent.data.modify_user(author.id, sender_data)
						flag2 = self.parent.data.modify_user(recipient_id, recipient_data)

						# TODO: Finish

				except ValueError:
					return await self.parent.send_message_w_fields(message, "Invalid user", "Use pay <@user> <amount>", discord.Color.red(), "Invalid argument @user", "Try mentioning a user")

			return await self.parent.send_message_w_fields(message, "Invalid user", "Use pay <@user> <amount>", discord.Color.red(), "Invalid argument @user", "Try mentioning a user")

	def __args__(self) -> str:
		return "<@user> <amount>"

	def __help__(self) -> str:
		return "Pay someone credits"

class CommandHandler:

	def __init__(self, parent: "gamble.GambleBot"):
		self.parent = parent
		self.slots_manager = SlotsManager()
		self.mentions = discord.AllowedMentions(replied_user = False)

		self.cmds: Dict[str, Command] = {
			"bal": Bal(parent),
			"roll": Roll(parent),
			"slots": Slots(parent),
			"fslots": FastSlots(parent),
			"daily": Daily(parent),
			"help": Help(parent)
		}

		self._help_fields = []

		for cmd_name, cmd_object in self.cmds.items():
			args = cmd_object.__args__()
			help_msg = cmd_object.__help__()

			if args.__len__():
				if isinstance(args, str):
					self._help_fields.append(f"{cmd_name} {args}")
					self._help_fields.append(help_msg)

				elif hasattr(args, "__iter__"):
					for arg in args:
						self._help_fields.append(f"{cmd_name} {arg}")
						self._help_fields.append(help_msg)
			else:
				self._help_fields.append(cmd_name)
				self._help_fields.append(help_msg)

		self.rate_limit: Dict[int, int] = {}

	@property
	def next_rate_limit(self) -> int:
		return int(time.time() + 5)

	async def receive(self, cmd: str, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild] = None) -> None:
		allow = False

		if author.id not in self.rate_limit:
			self.rate_limit[author.id] = self.next_rate_limit
			allow = True
		elif self.rate_limit[author.id] <= int(time.time()):
			allow = True

		if allow:
			if cmd in self.cmds:
				await self.cmds[cmd](args, message, author, guild)
				return # Don't want to return the output from the command as it's sometimes non-None

			prefix = "g!" if guild is None else self.parent.data.read_guild(guild.id)["cmd_prefix"]

			await self.parent.send_message(message, "Invalid command", f'No command called "{cmd}" exists, try using {prefix}help', discord.Color.red(), True)
			return

		await self.parent.send_message(message, "Rate Limit", "You're being rate limited, try again in a few seconds", discord.Color.dark_purple(), True)