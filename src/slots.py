from typing import TypedDict, Tuple, List
import asyncio
import discord
import gamble
import random

class Element(TypedDict):
	emote: str
	chance: float
	multiplier: float

class Manager:

	def __init__(self):
		self.apple:       Element = {"emote": "apple",       "chance": .70,  "multiplier": 0.5 }
		self.green_apple: Element = {"emote": "green_apple", "chance": .60,  "multiplier": 0.75}
		self.tangerine:   Element = {"emote": "tangerine",   "chance": .50,  "multiplier": 1   }
		self.pear:        Element = {"emote": "pear",        "chance": .45,  "multiplier": 1.25}
		self.lemon:       Element = {"emote": "lemon",       "chance": .35,  "multiplier": 1.75}
		self.melon:       Element = {"emote": "melon",       "chance": .30,  "multiplier": 2.5 }
		self.strawberry:  Element = {"emote": "strawberry",  "chance": .20,  "multiplier": 3   }
		self.peach:       Element = {"emote": "peach",       "chance": .15,  "multiplier": 4   }
		self.kiwi:        Element = {"emote": "kiwi",        "chance": .10,  "multiplier": 4.5 }
		self.blueberry:   Element = {"emote": "blueberries", "chance": .10,  "multiplier": 5   }
		self.grapes:      Element = {"emote": "grapes",      "chance": .05,  "multiplier": 8   }
		self.cherry:      Element = {"emote": "cherries",    "chance": .025, "multiplier": 10  }

		self.slots: Tuple[Element] = (
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

class Machine:

	def __init__(self, parent: "gamble.GambleBot", bet: int, rows: int = 10):
		self.parent = parent
		self.slots: List[List[Element]] = []
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

			await self.slot_message.edit(content = None, embed = self.parent.build_embed("Slot Machine", f'**=** :{self.slots[1][0]["emote"]}: :{self.slots[1][1]["emote"]}: :{self.slots[1][2]["emote"]}: **=**',
				discord.Color.gold(), "You won!", f"You got {win_amount} credit{'' if win_amount == 1 else 's'}"), allowed_mentions = self.parent.command_handler.mentions)

			# Already locked
			user_data = await self.parent.data.read_user(author.id, True)
			user_data["bal"] += win_amount

			self.parent.logger.log_gain(author.id, win_amount, f"slot machine win on {self.slots[1][0]['emote']} with multiplier of {self.slots[1][0]['multiplier']} on a bet of {self.bet}")

			if not await self.parent.data.modify_user(author.id, user_data, True):
				self.parent.logger.log_data_failure("users", author.id, "slot machine", user_data)
				await self.parent.send_message(message, "Error", "Failed to save user data", discord.Color.red(), True)

		else:
			await self.slot_message.edit(content = None, embed = self.parent.build_embed("Slot Machine", f'= :{self.slots[1][0]["emote"]}: :{self.slots[1][1]["emote"]}: :{self.slots[1][2]["emote"]}: =',
				discord.Color.gold()), allowed_mentions = self.parent.command_handler.mentions)

	async def roll(self, message: discord.Message, fast: bool = False):
		async def do_a_barrel_roll():
			await asyncio.sleep(1)
			self.new_row()
			await self.slot_message.edit(content = self.__str__(), allowed_mentions = self.parent.command_handler.mentions)

		self.slot_message = await self.parent.send_raw_message(message, self.__str__())
		for _ in range(self.slots.__len__() - 3):
			await do_a_barrel_roll()

		if not fast:
			await asyncio.sleep(1)

	def __str__(self) -> str:
		return f'''** **   :{self.slots[2][0]["emote"]}: :{self.slots[2][1]["emote"]}: :{self.slots[2][2]["emote"]}:
{"**=**" if self.win else "="} :{self.slots[1][0]["emote"]}: :{self.slots[1][1]["emote"]}: :{self.slots[1][2]["emote"]}: {"**=**" if self.win else "="}
    :{self.slots[0][0]["emote"]}: :{self.slots[0][1]["emote"]}: :{self.slots[0][2]["emote"]}:'''