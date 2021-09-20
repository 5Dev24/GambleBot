from typing import Optional, Dict, List
from collections import defaultdict
import blackjack
import datetime
import discord
import asyncio
import random
import gamble
import random
import slots
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
			target_id = args[0]
			if target_id.startswith("<@") and target_id.endswith(">"):
				target_id = target_id[2:-1]
				if target_id.startswith("!"):
					target_id = target_id[1:]

				try:
					target_id = int(target_id)

					if target_id == author.id:
						bal = (await self.parent.data.read_user(author.id))["bal"]
						await self.parent.send_message(message, "Your balance is", f"{bal} credit{'' if bal == 1 else 's'}", discord.Color.gold())
						return

					target: discord.User = self.parent.get_user(target_id)

					if target is None:
						await self.parent.send_message(message, "Can't find user", f"Can't find a user by the id {target_id}", discord.Color.red())
					else:
						bal = (await self.parent.data.read_user(target_id))['bal']
						await self.parent.send_message(message, f"{target.name}'s balance is", f"{bal} credit{'' if bal == 1 else 's'}", discord.Color.gold())

				except ValueError:
					await self.parent.send_message_w_fields(message, "Invalid user", "Use bal [@user]", discord.Color.red(), "Invalid argument @user", "Try mentioning a user")

			else:
				await self.parent.send_message_w_fields(message, "Invalid user", "Use bal [@user]", discord.Color.red(), "Invalid argument @user", "Try mentioning a user")

		else:
			bal = (await self.parent.data.read_user(author.id))["bal"]
			await self.parent.send_message(message, "Your balance is", f"{bal} credit{'' if bal == 1 else 's'}", discord.Color.gold())

	def __args__(self) -> str:
		return "[@user]"

	def __help__(self) -> str:
		return "Check your balance"

class Roll(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild]) -> None:
		async with self.parent.user_locker.lock(author.id):
			user_data = await self.parent.data.read_user(author.id, True)
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

				self.parent.logger.log_gain(author.id, gain, f"roll of {total}")

				user_data["roll"] = now
				if not await self.parent.data.modify_user(author.id, user_data, True):
					self.parent.logger.log_data_failure("users", author.id, "roll", user_data)
					await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)

			else:
				await self.parent.send_message(message, "You're last roll was too recent", f"Try again in {datetime.timedelta(seconds = user_data['roll'] + 7200 - now)}", discord.Color.red())

	def __help__(self) -> str:
		return "Roll 3 dies every 2 hours for credits"

class Daily(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild]) -> None:
		async with self.parent.user_locker.lock(author.id):
			user_data = await self.parent.data.read_user(author.id, True)
			today = datetime.datetime.now().strftime("%Y%m%d")

			if today == user_data["daily"]:
				await self.parent.send_message(message, "You've already claimed you daily", "Try again tomorrow", discord.Color.red())
			else:
				user_data["bal"] += 1000

				self.parent.logger.log_gain(author.id, 1000, f"daily on {today}")

				user_data["daily"] = today
				await self.parent.send_message(message, "Take your daily credits!", f"You now have {user_data['bal']} credits", discord.Color.gold())

				if not await self.parent.data.modify_user(author.id, user_data, True):
					self.parent.logger.log_data_failure("users", author.id, "daily", user_data)
					await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)

	def __help__(self) -> str:
		return "Collect 1000 credits daily"

class Help(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild]) -> None:
		await self.parent.send_message_w_fields(message, "Help", "Below is a list of all commands and their help messages", discord.Color.gold(), *self.parent.command_handler._help_fields)

	def __help__(self) -> str:
		return "See all help messages"

class Slots(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild]) -> None:
		if args.__len__():
			bet = args[0]

			try:
				bet = int(bet)

			except ValueError:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use slots <bet>", discord.Color.red(), "Invalid argument bet", "Try specifying a positive integer")
				return

			if bet < 0:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use slots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be positive")
				return

			if bet < 20:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use slots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be at least 20 credits")
				return

			if bet > 2500:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use slots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet cannot be greater than 2500 credits")
				return

			async with self.parent.user_locker.lock(author.id): # When doing a balance check, we need to lock user data to prevent a negative balance
				user_data = await self.parent.data.read_user(author.id, True)

				if user_data["bal"] < bet:
					await self.parent.send_message_w_fields(message, "Invalid bet", "Use slots <bet>", discord.Color.red(), "Invalid argument bet", "You don't have enough credits to make that bet")
					return

				user_data["bal"] -= bet

				self.parent.logger.log_loss(author.id, bet, "slots payment")

				if not await self.parent.data.modify_user(author.id, user_data, True):
					self.parent.logger.log_data_failure("users", author.id, "slots", user_data)
					await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)
				else:
					machine = slots.Machine(self.parent, bet)
					await machine.roll(message)
					await machine.payout(message, author)

		else:
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
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use fslots <bet>", discord.Color.red(), "Invalid argument bet", "Try specifying a positive whole number")
				return

			if bet < 0:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use fslots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be positive")
				return

			if bet < 20:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use fslots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be at least 20 credits")
				return

			if bet > 2500:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use fslots <bet>", discord.Color.red(), "Invalid argument bet", "Your bet cannot be greater than 2500 credits")
				return

			async with self.parent.user_locker.lock(author.id): # When doing a balance check, we need to lock user data to prevent a negative balance
				user_data = await self.parent.data.read_user(author.id, True)

				if user_data["bal"] < bet:
					await self.parent.send_message_w_fields(message, "Invalid bet", "Use fslots <bet>", discord.Color.red(), "Invalid argument bet", "You don't have enough credits to make that bet")
					return

				user_data["bal"] -= bet

				self.parent.logger.log_loss(author.id, bet, "fslots payment")

				if not await self.parent.data.modify_user(author.id, user_data, True):
					self.parent.logger.log_data_failure("users", author.id, "fslots", user_data)
					await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)
				else:
					machine = slots.Machine(self.parent, bet, 3)
					await machine.roll(message, True)
					await machine.payout(message, author)

		else:
			await self.parent.send_message_w_fields(message, "Invalid usage", "Use fslots <bet>", discord.Color.red(), "Missing argument", "You need to specify a bet")

	def __args__(self) -> str:
		return "<bet>"

	def __help__(self) -> str:
		return "Spin the wheel quickly"

class Pay(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild] = None) -> None:
		if args.__len__() < 2:
			await self.parent.send_message_w_fields(message, "Invalid usage", "Use pay <@user> <amount>", discord.Color.red(), f"Missing argument{'' if args.__len__() == 1 else 's'}", "You need to specify the recipient and the amount of credits to send")
			return

		amount_to_pay = args[1]

		try:
			amount_to_pay = int(amount_to_pay)
		except ValueError:
			await self.parent.send_message_w_fields(message, "Invalid amount", "Use pay <@user> <amount>", discord.Color.red(), "Invalid argument amount", "Try specifying a positive whole number")
			return

		if amount_to_pay <= 0:
			await self.parent.send_message_w_fields(message, "Invalid amount", "Use pay <@user> <amount>", discord.Color.red(), "Invalid argument amount", "The amount must be positive and not zero")
			return

		async with self.parent.user_locker.lock(author.id): # Because we're checking the balance, we need to lock data after we check as two payments close to each other can both pass this check and lead to a negative balance
			sender_data = await self.parent.data.read_user(author.id, True)

			if sender_data["bal"] < amount_to_pay:
				await self.parent.send_message_w_fields(message, "Invalid amount", "Use pay <@user> <amount>", discord.Color.red(), "Invalid argument amount", f"You don't have enought credits to send {amount_to_pay}")
				return

			recipient_id = args[0]
			if recipient_id.startswith("<@") and recipient_id.endswith(">"):
				recipient_id = recipient_id[2:-1]
				if recipient_id.startswith("!"):
					recipient_id = recipient_id[1:]

				try:
					recipient_id = int(recipient_id)

					if recipient_id == author.id:
						await self.parent.send_message(message, "What? Why?", "You can't pay yourself", discord.Color.red())
						return

					recipient: discord.User = self.parent.get_user(recipient_id)

					if recipient is None:
						await self.parent.send_message(message, "Can't find user", f"Can't find a user by the id {recipient_id}", discord.Color.red())
						return

					# This check is done and cancels the pay if the recipient has their data lock acquired to prevent deadlock

					# User A's Pay locks User A's Lock
					# User B's Pay locks User B's Lock
					# User A's Pay wants User B's Lock
					# User B's Pay wants User A's Lock
					# Neither can get the lock they want and the two Users' Locks remain locked and cannot unlock
					# Deadlock!

					if not self.parent.user_locker.locked(recipient_id):
						async with self.parent.user_locker.lock(recipient_id):
							recipient_data = await self.parent.data.read_user(recipient_id, True)

							sender_data["bal"] -= amount_to_pay
							recipient_data["bal"] += amount_to_pay

							self.parent.logger.log_transation(author.id, recipient_id, amount_to_pay)

							flag1 = not await self.parent.data.modify_user(author.id, sender_data, True)
							flag2 = not await self.parent.data.modify_user(recipient_id, recipient_data, True)

							if flag1:
								self.parent.logger.log_data_failure("users", author.id, "pay sender", sender_data)

							if flag2:
								self.parent.logger.log_data_failure("users", recipient_id, "pay recipient", recipient_data)

							if flag1 and flag2:
								await self.parent.send_message(message, "Error", "Failed to save both user's data", discord.Color.red(), True)
							elif flag1:
								await self.parent.send_message(message, "Error", "Failed to save sender's data", discord.Color.red(), True)
							elif flag2:
								await self.parent.send_message(message, "Error", "Failed to save recipient's data", discord.Color.red(), True)
							else:
								await self.parent.send_message_w_fields(message, "Payment complete", f"{amount_to_pay} credit{'' if amount_to_pay == 1 else 's'} has been sent", discord.Color.gold(),
									"Your new balance", f'{sender_data["bal"]} credit{"" if sender_data["bal"] == 1 else "s"}',
									f"{recipient.name}'s new balance", f'{recipient_data["bal"]} credit{"" if recipient_data["bal"] == 1 else "s"}')
					else:
						await self.parent.send_message(message, "Can't pay user", f"{recipient.name} is running commands that could affect their balance, try paying them later", discord.Color.dark_red(), True)

				except ValueError:
					await self.parent.send_message_w_fields(message, "Invalid user", "Use pay <@user> <amount>", discord.Color.red(), "Invalid argument @user", "Try mentioning a user")

			else:
				await self.parent.send_message_w_fields(message, "Invalid user", "Use pay <@user> <amount>", discord.Color.red(), "Invalid argument @user", "Try mentioning a user")

	def __args__(self) -> str:
		return "<@user> <amount>"

	def __help__(self) -> str:
		return "Pay someone credits"

class Flip(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild] = None) -> None:
		if args.__len__():
			bet = args[0]

			try:
				bet = int(bet)

			except ValueError:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use flip <bet>", discord.Color.red(), "Invalid argument bet", "Try specifying a positive integer")
				return

			if bet < 0:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use flip <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be positive")
				return

			if bet < 100:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use flip <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be at least 100 credits")
				return

			if bet > 1000:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use flip <bet>", discord.Color.red(), "Invalid argument bet", "Your bet cannot be greater than 1000 credits")
				return

			async with self.parent.user_locker.lock(author.id):
				user_data = await self.parent.data.read_user(author.id, True)

				if user_data["bal"] < bet:
					await self.parent.send_message_w_fields(message, "Invalid bet", "Use flip <bet>", discord.Color.red(), "Invalid argument bet", "You don't have enough credits to make that bet")
					return

				if random.randint(0, 1): # Actual 50/50
					self.parent.logger.log_gain(author.id, bet, "flip")
					user_data["bal"] += bet
					await self.parent.send_message(message, "Heads!", f"Here's your {bet} credit{'' if bet == 1 else 's'}", discord.Color.gold())
				else:
					self.parent.logger.log_loss(author.id, bet, "flip")
					user_data["bal"] -= bet
					await self.parent.send_message(message, "Tails!", "Better luck next time", discord.Color.gold())

				if not await self.parent.data.modify_user(author.id, user_data, True):
					self.parent.logger.log_data_failure("users", author.id, "flip", user_data)
					await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)

		else:
			await self.parent.send_message_w_fields(message, "Invalid usage", "Use flip <bet>", discord.Color.red(), "Missing argument", "You need to specify a bet")

	def __args__(self) -> str:
		return "<bet>"

	def __help__(self) -> str:
		return "Flip a coin and hope it lands on heads"

class Odds(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild] = None) -> None:
		if args.__len__():
			cmd = args[0].lower()

			if cmd == "roll":
				await self.parent.send_message_w_fields(message, "Roll odds", "Below are the chances for getting any roll", discord.Color.gold(),
					"3 or 18", "`0.463%`", "4 or 17", "`1.389%`", "5 or 16", "`2.778%`", "6 or 15", "`4.630%`", "7 or 14", "`6.944%`", "8 or 13", "`9.722%`", "9 or 12", "`11.574%`", "10 or 11", "`12.500%`")

			elif cmd == "slots" or cmd == "fslots":
				await self.parent.send_message_w_fields(message, f"{cmd.title()} odds", "Below are the chances for rolling any fruit", discord.Color.gold(),
					"Your chances of winning are 60%", "Then a random fruit is selected based off this table, format:", "Fruit", "`multiplier` @ `chance`",
					"Apple", "`0.5` @ `19.858%`", True, "Green Apple", "`0.75` @ `17.021%`", True, "Tangerine", "`1` @ `14.184%`", True, "Pear", "`1.25` @ `12.766%`", True, "Lemon", "`1.75` @ `9.929%`", True,
					"Melon", "`2.5` @ `8.511%`", True, "Strawberry", "`3` @ `5.674%`", True, "Peach", "`4` @ `4.255%`", True, "Kiwi", "`4.5` @ `2.837%`", True, "Blueberry", "`5` @ `2.837%`", True,
					"Grapes", "`8` @ `1.418%`", True, "Cherry", "`10` @ `0.709%`", True)

			elif cmd == "flip":
				await self.parent.send_message_w_fields(message, "Flip odds", "Well, the odds are quite simple", discord.Color.gold(),
					"Heads (win)", "50%", "Tails (loss)", "50%")

			else:
				await self.parent.send_message_w_fields(message, "Invalid usage", "Use odds <cmd>", discord.Color.red(), "Invalid argument <cmd>", "You can only specify roll, slots, fslots, or flip")

		else:
			await self.parent.send_message_w_fields(message, "Invalid usage", "Use odds <cmd>", discord.Color.red(), "Missing argument", "You need to specify a command")

	def __args__(self) -> str:
		return "<cmd>"

	def __help__(self) -> str:
		return "Find out the odds of certain games"

class Blackjack(Command):

	async def __call__(self, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild] = None) -> None:
		if guild is None: # In DMs
			await self.parent.send_message_w_fields(message, "Invalid playing place", "Use blackjack <bet> in a server", discord.Color.red(),
				"Blackjack can only be played in servers", "This is because Gamble needs to be able to clear reactions for the game to work")
			return

		if args.__len__():
			bet = args[0]

			try:
				bet = int(bet)

			except ValueError:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use blackjack <bet>", discord.Color.red(), "Invalid argument bet", "Try specifying a positive integer")
				return

			if bet < 0:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use blackjack <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be positive")
				return

			if bet < 50:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use blackjack <bet>", discord.Color.red(), "Invalid argument bet", "Your bet must be at least 50 credits")
				return

			if bet > 5000:
				await self.parent.send_message_w_fields(message, "Invalid bet", "Use blackjack <bet>", discord.Color.red(), "Invalid argument bet", "Your bet cannot be greater than 5000 credits")
				return

			async with self.parent.user_locker.lock(author.id):
				user_data = await self.parent.data.read_user(author.id, True)

				if user_data["bal"] < bet:
					await self.parent.send_message_w_fields(message, "Invalid bet", "Use blackjack <bet>", discord.Color.red(), "Invalid argument bet", "You don't have enough credits to make that bet")
					return

				self.parent.logger.log_loss(author.id, bet, "blackjack payment")
				user_data["bal"] -= bet

				if not await self.parent.data.modify_user(author.id, user_data, True):
					self.parent.logger.log_data_failure("users", author.id, "blackjack", user_data)
					await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)
				else:
					await self.parent.command_handler.blackjack_manager.start_game(message, bet)

		else:
			await self.parent.send_message_w_fields(message, "Invalid usage", "Use blackjack <bet>", discord.Color.red(), "Missing argument", "You need to specify a bet")

	def __args__(self) -> str:
		return "<bet>"

	def __help__(self) -> str:
		return "Play a game of blackjack"

class CommandHandler:

	def __init__(self, parent: "gamble.GambleBot"):
		self.parent = parent
		self.mentions = discord.AllowedMentions(replied_user = False)

		self.slots_manager = slots.Manager()
		self.blackjack_manager = blackjack.Manager(parent)

		self.cmds: Dict[str, Command] = {
			"bal": Bal(parent),
			"roll": Roll(parent),
			"slots": Slots(parent),
			"fslots": FastSlots(parent),
			"pay": Pay(parent),
			"flip": Flip(parent),
			"daily": Daily(parent),
			"blackjack": Blackjack(parent),
			"odds": Odds(parent),
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

		self.rate_limit_locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
		self.rate_limit: Dict[int, int] = {}

	@property
	def next_rate_limit(self) -> int:
		return int(time.time() + 2)

	async def receive(self, cmd: str, args: List[str], message: discord.Message, author: discord.User, guild: Optional[discord.Guild] = None) -> None:
		if not self.rate_limit_locks[author.id].locked():
			async with self.rate_limit_locks[author.id]:
				allow = False

				if author.id not in self.rate_limit:
					self.rate_limit[author.id] = self.next_rate_limit
					allow = True
				elif self.rate_limit[author.id] <= int(time.time()):
					allow = True

				if allow:
					if cmd in self.cmds:
						await self.cmds[cmd](args, message, author, guild)
					else:
						prefix = "g!" if guild is None else (await self.parent.data.read_guild(guild.id))["cmd_prefix"]
						await self.parent.send_message(message, "Invalid command", f'No command called "{cmd}" exists, try using {prefix}help', discord.Color.red(), True)

				else:
					await self.parent.send_message(message, "Rate Limit", "You're being rate limited, try again in a few seconds", discord.Color.dark_purple(), True)

		else:
			await self.parent.send_message(message, "Rate Limit", "You're being rate limited, wait for any commands you've ran to finish and try again in a few seconds", discord.Color.dark_purple(), True)