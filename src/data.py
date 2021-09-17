from typing import TypedDict, Dict, Any
from collections import defaultdict
from threading import RLock
from json import dump, load
import fasteners
import datetime
import gamble
import time
import os

class Locker:

	def __init__(self):
		self.data_locks: Dict[int, RLock] = defaultdict(RLock)

	def acquire(self, object_id: int):
		self.data_locks[object_id].acquire()

	def release(self, object_id: int):
		self.data_locks[object_id].release()

	def lock(self, object_id: int) -> RLock:
		return self.data_locks[object_id]

class UserDataType(TypedDict):
	bal: int
	roll: int
	blackjack: int
	daily: str

def _default_user_data() -> UserDataType:
	return UserDataType(bal = 0, roll = 0, blackjack = 0, daily = (datetime.datetime.now() - datetime.timedelta(days = 1)).strftime("%Y%m%d"))

class GuildDataType(TypedDict):
	cmd_channel: int
	cmd_prefix: str

def _default_guild_data() -> GuildDataType:
	return GuildDataType(cmd_channel = -1, cmd_prefix = "g!")

class Cached(TypedDict):
	data: Dict[str, Any]
	last_access: int

class DataHandler:

	_data_root: str = None # Set at runtime in __main__

	def __init__(self, parent: "gamble.GambleBot"):
		self.parent = parent
		self._cache: Dict[str, Dict[int, Cached]] = {
			"users": {},
			"guilds": {}
		} # Prevent as many reads

	def __modify(self, object_id: int, object_type: str, data: Dict[str, Any]) -> bool:
		"""A data RLock is assumed to already be acquired"""
		try:
			object_file = os.path.join(DataHandler._data_root, object_type, f"{object_id}.json")

			write_lock = fasteners.InterProcessReaderWriterLock(object_file)

			got = False
			try:
				got = write_lock.acquire_write_lock()
				with open(object_file, "w") as object_file:
					dump(data, object_file, separators = (",", ":"))
					return True

			finally:
				if got:
					write_lock.release_write_lock()

		except (IOError, PermissionError):
			return False

	def __read(self, object_id: int, object_type: str) -> Dict[str, Any]:
		"""A data RLock is assumed to already be acquired"""
		try:
			object_file = os.path.join(DataHandler._data_root, object_type, f"{object_id}.json")

			read_lock = fasteners.InterProcessReaderWriterLock(object_file)

			got = False
			try:
				got = read_lock.acquire_read_lock()
				with open(object_file, "r") as object_file:
					return load(object_file)

			finally:
				if got:
					read_lock.release_read_lock()

		except (IOError, FileNotFoundError, PermissionError):
			return None

	def __exists(self, object_id: int, object_type: str) -> bool:
		"""A data RLock is assumed to already be acquired"""
		return os.path.isfile(os.path.join(DataHandler._data_root, object_type, f"{object_id}.json"))

	def modify_user(self, user_id: int, data: UserDataType) -> bool:
		with self.parent.user_locker.lock(user_id):
			tmp = self.__modify(user_id, "users", data)

			if tmp:
				self._cache["users"][user_id] = Cached(data = data, last_access = int(time.time()))

			return tmp

	def read_user(self, user_id: int) -> UserDataType:
		with self.parent.user_locker.lock(user_id):
			if user_id in self._cache["users"]:
				self._cache["users"][user_id]["last_access"] = int(time.time())
				return self._cache["users"][user_id]["data"]

			if self.__exists(user_id, "users"):
				read = self.__read(user_id, "users")
				self._cache["users"][user_id] = Cached(data = read, last_access = int(time.time()))
				return read

			default = _default_user_data()
			self._cache["users"][user_id] = Cached(data = default, last_access = int(time.time()))
			return default

	def modify_guild(self, guild_id: int, data: GuildDataType) -> bool:
		with self.parent.guild_locker.lock(guild_id):
			tmp = self.__modify(guild_id, "guilds", data)

			if tmp:
				self._cache["guilds"][guild_id] = Cached(data = data, last_access = int(time.time()))

			return tmp

	def read_guild(self, guild_id: int) -> GuildDataType:
		with self.parent.guild_locker.lock(guild_id):
			if guild_id in self._cache["guilds"]:
				self._cache["guilds"][guild_id]["last_access"] = int(time.time())
				return self._cache["guilds"][guild_id]["data"]

			if self.__exists(guild_id, "guilds"):
				read = self.__read(guild_id, "guilds")
				self._cache["guilds"][guild_id] = Cached(data = read, last_access = int(time.time()))
				return read

			default = _default_guild_data()
			self._cache["guilds"][guild_id] = Cached(data = default, last_access = int(time.time()))
			return default
