from collections import defaultdict
from typing import Dict
import discord
import asyncio
import gamble
import random

class Manager:

	def __init__(self, parent: "gamble.GambleBot"):
		self.parent = parent
		self._games_lock: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
		self._games: Dict[int, Game] = {}

	async def start_game(self, message: discord.Message, bet: int):
		blackjack_game = Game(self, message.author.id, bet)
		await blackjack_game.finish_setup(message)

		if not blackjack_game.dead: # If game instantly ended (naturals), don't add it to array
			async with self._games_lock[blackjack_game.game_id]:
				self._games[blackjack_game.game_id] = blackjack_game

	async def is_owned_and_active_game(self, game_id: int, user_id: int):
		async with self._games_lock[game_id]:
			return game_id in self._games and self._games[game_id].owner_id == user_id and not self._games[game_id].dead

	async def update(self, game_id: int, emoji: str) -> bool:
		if self._games_lock[game_id].locked():
			return # Ignore inputs while game is busy

		async with self._games_lock[game_id]:
			await self._games[game_id].update(emoji)

	async def kill_game(self, game_id: int, kill_message: str):
		if self._games[game_id].dead: return

		self._games[game_id].dead = True

		await self._games[game_id].game_message.edit(content = None, embed = self.parent.build_embed("Blackjack", f"Game killed because {kill_message}",
			discord.Color.red()), allowed_mentions = self.parent.command_handler.mentions)
		await self._games[game_id].game_message.clear_reactions()

		del self._games[game_id]

	async def end_game(self, game: "Game", *fields):
		if game.dead: return

		game.dead = True

		await game.message(discord.Color.gold(), *fields)
		await game.game_message.clear_reactions()

		if game.game_id in self._games:
			del self._games[game.game_id]

class Game:

	__map = { "1️⃣": 1, "2️⃣": 2, "3️⃣": 3 }

	def __init__(self, parent: Manager, owner_id: int, bet: int):
		self.parent = parent
		self.game_id: int = -1
		self.owner_id = owner_id
		self.bet = bet
		self.game_message: discord.Message = None
		self.dead: bool = False
		self.has_doubled = False

		self.hide_dealers_second = True
		self.dealers_hand = ""
		self.players_hand = ""

	async def finish_setup(self, message: discord.Message) -> None:
		if self.game_message is not None: return

		self.game_message = await self.parent.parent.send_message(message, "Blackjack", f"Setting up game", discord.Color.dark_red())
		self.game_id = self.game_message.id

		await self.message(discord.Color.dark_blue(), "Lets deal some cards", "Best of luck!")

		await asyncio.sleep(.5)

		self.players_hand += Deck.draw_card(self.game_id)
		self.dealers_hand += Deck.draw_card(self.game_id)
		self.players_hand += Deck.draw_card(self.game_id)
		self.dealers_hand += Deck.draw_card(self.game_id)

		# Check for naturals, player's data lock is still locked from blackjack command

		dealer_natural = player_natural = False

		if self.players_hand_value == 21:
			player_natural = True

		if Deck.hand_value(self.dealers_hand) == 21:
			dealer_natural = True

		if player_natural and dealer_natural:
			self.hide_dealers_second = False

			await self.parent.end_game(self, "Both the dealer and yourself drew naturals", f"Your bet of {self.bet} credit{'' if self.bet == 1 else 's'} will be given back",
				f"Dealer's hand ({self.dealers_hand_value})", self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr)

			user_data = await self.parent.parent.data.read_user(self.owner_id, True)

			self.parent.parent.logger.log_gain(self.owner_id, self.bet, "blackjack dealer & player natural")
			user_data["bal"] += self.bet

			if not await self.parent.parent.data.modify_user(self.owner_id, user_data, True):
				self.parent.parent.logger.log_data_failure("users", self.owner_id, "blackjack dealer & player natural", user_data)
				await self.parent.parent.send_message(self.game_message, "Error", "Failed to save user data", discord.Color.red())

			return

		elif player_natural:
			self.hide_dealers_second = False
			win_amount = int(self.bet * 2.5)

			await self.parent.end_game(self, "Your drew a natural", f"You win {win_amount} credit{'' if win_amount == 1 else 's'}!",
				f"Dealer's hand ({self.dealers_hand_value})", self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr)

			user_data = await self.parent.parent.data.read_user(self.owner_id, True)

			self.parent.parent.logger.log_gain(self.owner_id, win_amount, "blackjack player natural")
			user_data["bal"] += win_amount

			if not await self.parent.parent.data.modify_user(self.owner_id, user_data, True):
				self.parent.parent.logger.log_data_failure("users", self.owner_id, "blackjack player natural", user_data)
				await self.parent.parent.send_message(self.game_message, "Error", "Failed to save user data", discord.Color.red())

			return

		elif dealer_natural:
			self.hide_dealers_second = False

			await self.parent.end_game(self, "The dealer drew a natural", "The house keeps it all", f"Dealer's hand ({self.dealers_hand_value})",
				self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr)

			return

		user_data = await self.parent.parent.data.read_user(self.owner_id, True)
		can_double = self.players_hand_value in (9, 10, 11) and user_data["bal"] >= self.bet

		await self.message(discord.Color.blue(), f"Dealer's hand ({self.dealers_hand_value} + ?)",
			self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr,
			"1️⃣", "Hit", True, "2️⃣", "Stand", True, *(("3️⃣", "Double") if can_double else tuple()))

		await self.game_message.add_reaction("1️⃣")
		await self.game_message.add_reaction("2️⃣")

		if can_double:
			await self.game_message.add_reaction("3️⃣") # Doubling

	async def message(self, color: discord.Colour, *fields) -> None:
		await self.game_message.edit(content = None, embed = self.parent.parent.build_embed("Blackjack", discord.embeds.EmptyEmbed, color, *fields), allowed_mentions = self.parent.parent.command_handler.mentions)

	async def fix_reaction(self, reaction: int, options: int) -> None:
		if self.dead: return

		if reaction <= 3:
			await self.game_message.clear_reaction("3️⃣")

		if reaction <= 2:
			await self.game_message.clear_reaction("2️⃣")

		if reaction <= 1:
			await self.game_message.clear_reaction("1️⃣")

			if options >= 1:
				await self.game_message.add_reaction("1️⃣")

		if options >= 2 and reaction <= 2:
			await self.game_message.add_reaction("2️⃣")

		if options >= 3 and reaction <= 3:
			await self.game_message.add_reaction("3️⃣")

	async def update(self, emoji: str) -> None:
		if self.dead: return

		if emoji not in Game.__map:
			return

		selection = Game.__map[emoji]

		if selection == 1: # Hit
			self.players_hand += Deck.draw_card(self.game_id)

			if self.players_hand_value > 21:
				self.hide_dealers_second = False

				await self.parent.end_game(self, "You busted", "You went over 21", f"Dealer's hand ({self.dealers_hand_value})",
					self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr)

				return

			if self.players_hand_value == 21: # Auto-stand
				await self.message(discord.Color.blue(), f"Dealer's hand ({self.dealers_hand_value} + ?)",
					self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr,
					"You hit 21", "Automically standing")
				await asyncio.sleep(.5)
				await self.update("2️⃣")
				return

			await self.message(discord.Color.blue(), f"Dealer's hand ({self.dealers_hand_value} + ?)",
				self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr,
				"1️⃣", "Hit", True, "2️⃣", "Stand", True)

		elif selection == 2: # Stand
			self.hide_dealers_second = False
			
			if self.dealers_hand_value < 17:
				await self.message(discord.Color.blue(), f"Dealer's hand ({self.dealers_hand_value})",
					self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr,
					"1️⃣", "Hit", True, "2️⃣", "Stand", True)

				while self.dealers_hand_value < 17:
					await asyncio.sleep(.5)
					self.dealers_hand += Deck.draw_card(self.game_id)
					await self.message(discord.Color.blue(), f"Dealer's hand ({self.dealers_hand_value})",
						self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr,
						"1️⃣", "Hit", True, "2️⃣", "Stand", True)

			if self.dealers_hand_value > 21: # Dealer busted
				win_amount = self.bet * 2

				await self.parent.end_game(self, "Dealer busted", f"They went over 21, take your {win_amount} credit{'' if win_amount == 1 else 's'}",
					f"Dealer's hand ({self.dealers_hand_value})", self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr)

				async with self.parent.parent.user_locker.lock(self.owner_id):
					user_data = await self.parent.parent.data.read_user(self.owner_id, True)

					self.parent.parent.logger.log_gain(self.owner_id, win_amount, "blackjack dealer busted")
					user_data["bal"] += win_amount

					if not await self.parent.parent.data.modify_user(self.owner_id, user_data, True):
						self.parent.parent.logger.log_data_failure("users", self.owner_id, "blackjack dealer busted", user_data)
						await self.parent.parent.send_message(self.game_message, "Error", "Failed to save user data", discord.Color.red())

			elif self.dealers_hand_value < self.players_hand_value: # Player has higher cards that dealer
				win_amount = self.bet * 2

				await self.parent.end_game(self, "Dealer stands", f"Your hand is worth more, take your {win_amount} credit{'' if win_amount == 1 else 's'}",
					f"Dealer's hand ({self.dealers_hand_value})", self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr)

				async with self.parent.parent.user_locker.lock(self.owner_id):
					user_data = await self.parent.parent.data.read_user(self.owner_id, True)

					self.parent.parent.logger.log_gain(self.owner_id, win_amount, "blackjack player beat dealer")
					user_data["bal"] += win_amount

					if not await self.parent.parent.data.modify_user(self.owner_id, user_data, True):
						self.parent.parent.logger.log_data_failure("users", self.owner_id, "blackjack player beat dealer", user_data)
						await self.parent.parent.send_message(self.game_message, "Error", "Failed to save user data", discord.Color.red())

			elif self.dealers_hand_value == self.players_hand_value: # Stand off, tie
				await self.parent.end_game(self, "Stand-off", f"Both hands are equal, take your original bet of {self.bet} credit{'' if self.bet == 1 else 's'} back",
					f"Dealer's hand ({self.dealers_hand_value})", self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr)

				async with self.parent.parent.user_locker.lock(self.owner_id):
					user_data = await self.parent.parent.data.read_user(self.owner_id, True)

					self.parent.parent.logger.log_gain(self.owner_id, self.bet, "blackjack player tie dealer")
					user_data["bal"] += self.bet

					if not await self.parent.parent.data.modify_user(self.owner_id, user_data, True):
						self.parent.parent.logger.log_data_failure("users", self.owner_id, "blackjack player tie dealer", user_data)
						await self.parent.parent.send_message(self.game_message, "Error", "Failed to save user data", discord.Color.red())

			else: # Dealer is worth more
				await self.parent.end_game(self, "Dealer wins", "Looks like the dealer bested you this time",
					f"Dealer's hand ({self.dealers_hand_value})", self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr)

			return

		elif selection == 3 and not self.has_doubled: # Double
			async with self.parent.parent.user_locker.lock(self.owner_id):
				user_data = await self.parent.parent.data.read_user(self.owner_id, True)

				if self.players_hand.__len__() == 2 and self.players_hand_value in (9, 10, 11) and user_data["bal"] >= self.bet:
					self.parent.parent.logger.log_loss(self.owner_id, self.bet, "blackjack doubling down")
					user_data["bal"] -= self.bet

					self.bet *= 2
					self.has_doubled = True

					if not await self.parent.parent.data.modify_user(self.owner_id, user_data, True):
						self.parent.parent.logger.log_data_failure("users", self.owner_id, "blackjack doubling down", user_data)
						await self.parent.parent.send_message(self.game_message, "Error", "Failed to save user data", discord.Color.red())

			await self.message(discord.Color.blue(), "Doubled down!", f"Your bet has doubled to {self.bet} credit{'' if self.bet == 1 else 's'}", f"Dealer's hand ({self.dealers_hand_value} + ?)",
				self.dealers_hand_repr, f"Your hand ({self.players_hand_value})", self.players_hand_repr,
				"1️⃣", "Hit", True, "2️⃣", "Stand", True)

		try:
			await self.fix_reaction(selection, 2)
		except discord.errors.Forbidden:
			await self.parent.kill_game(self.game_id, "games cannot be played in DMs!")

	@property
	def dealers_hand_repr(self):
		output = ""

		for i in range(self.dealers_hand.__len__()):
			if i == 1 and self.hide_dealers_second:
				output += Deck.cards["?"]
			else:
				output += Deck.cards[self.dealers_hand[i]]

		return output

	@property
	def players_hand_repr(self):
		return "".join([Deck.cards[card] for card in self.players_hand])

	@property
	def dealers_hand_value(self):
		return Deck.hand_value(self.dealers_hand, self.hide_dealers_second)

	@property
	def players_hand_value(self):
		return Deck.hand_value(self.players_hand)

class Deck:

	__decks: Dict[int, str] = defaultdict(lambda: "23456789tjqka" * 4 * 6) # 6 decks
	cards: Dict[str, str] = {
		"2": "<:n2:889545006099091537>",
		"3": "<:n3:889545006501756962>",
		"4": "<:n4:889545006753411092>",
		"5": "<:n5:889545006539473008>",
		"6": "<:n6:889545006585643128>",
		"7": "<:n7:889545006258487297>",
		"8": "<:n8:889545006325563463>",
		"9": "<:n9:889545006677913600>",
		"t": "<:10:889545006707273759>",
		"j": "<:jack:889545006854074389>",
		"q": "<:queen:889545006635946035>",
		"k": "<:king:889545006828900373>",
		"a": "<:ace:889545006732431390>",
		"?": "<:unknown:889545006631751700>"
	}

	card_values: Dict[str, int] = {
		"2": 2, "3": 3, "4": 4, "5": 5,
		"6": 6, "7": 7, "8": 8, "9": 9,
		"t": 10, "j": 10, "q": 10, "k": 10,
		"a": 0
	}

	@staticmethod
	def draw_card(game_id: int) -> str:
		deck = Deck.__decks[game_id]

		if deck.__len__() > 60:
			selection = random.choice(deck)
			Deck.__decks[game_id] = deck.replace(selection, "", 1)
			return selection

		del Deck.__decks[game_id]
		return Deck.draw_card(game_id)

	@staticmethod
	def hand_value(hand: str, hide_second: bool = False) -> int:
		if hide_second:
			hand = hand[:1] + hand[2:]

		ace_count = hand.count("a")
		hand: int = sum([Deck.card_values[card] for card in hand])

		if ace_count > 1:
			hand += ace_count - 1
			ace_count = 1

		if ace_count == 1:
			if hand <= 10:
				hand += 11 # Hard
			else:
				hand += 1 # Soft

		return hand