from typing import Callable, TypedDict, Dict, Any
from collections import defaultdict
from threading import RLock
from json import dump, load
import datetime
import gamble
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

class DataHandler:

	_project_root: str = None # Set at runtime in __main__

	def __init__(self, parent: "gamble.GambleBot"):
		self.parent = parent
		self._cache: Dict[str, Dict[int, Dict[str, Any]]] = {
			"users": {},
			"guilds": {}
		} # Prevent as many reads

	def modify(self, object_id: int, object_type: str, data: Dict[str, Any]) -> bool:
		try:
			with self.parent.lockers.lock(object_id):
				with open(os.path.join(DataHandler._project_root, "data", object_type, f"{object_id}.json"), "w") as object_file:
					dump(data, object_file, separators = (",", ":"))
					return True

		except (IOError, PermissionError):
			return False

	def read(self, object_id: int, object_type: str) -> Dict[str, Any]:
		try:
			with self.parent.lockers.lock(object_id):
				with open(os.path.join(DataHandler._project_root, "data", object_type, f"{object_id}.json"), "r") as object_file:
					return load(object_file)

		except (IOError, FileNotFoundError, PermissionError):
			return None

	def exists(self, object_id: int, object_type: str) -> bool:
		with self.parent.lockers.lock(object_id):
			return os.path.isfile(os.path.join(DataHandler._project_root, "data", object_type, f"{object_id}.json"))

	def modify_user(self, user_id: int, data: UserDataType) -> bool:
		with self.parent.lockers.lock(user_id):
			tmp = self.modify(user_id, "users", data)

			if tmp:
				self._cache["users"][user_id] = data

			return tmp

	def read_user(self, user_id: int) -> UserDataType:
		with self.parent.lockers.lock(user_id):
			if user_id in self._cache["users"]:
				return self._cache["users"][user_id]

			if self.exists(user_id, "users"):
				read = self.read(user_id, "users")
				self._cache["users"][user_id] = read
				return read

			default = _default_user_data()
			self._cache["users"][user_id] = default
			return default

	def modify_guild(self, guild_id: int, data: GuildDataType) -> bool:
		with self.parent.lockers.lock(guild_id):
			tmp = self.modify(guild_id, "guilds", data)

			if tmp:
				self._cache["guilds"][guild_id] = data

			return tmp

	def read_guild(self, guild_id: int) -> GuildDataType:
		with self.parent.lockers.lock(guild_id):
			if guild_id in self._cache["guilds"]:
				return self._cache["guilds"][guild_id]

			if self.exists(guild_id, "guilds"):
				read = self.read(guild_id, "guilds")
				self._cache["guilds"][guild_id] = read
				return read

			default = _default_guild_data()
			self._cache["guilds"][guild_id] = default
			return default

"""
	CSV Method
		- Isn't good because if data fields (names) are changed, breaks and having to migrate seems awful
		- Would give smaller data files

	Cache method? idk

	def modify_user(self, user_id: int, data: UserDataType) -> bool:
		try:
			with self.parent.user_lockers.user_lock(user_id):
				with open(os.path.join(UserDataHandler._project_root, "data", "users", f"{user_id}.csv"), "w", newline = "") as user_file:
					csv.writer(user_file, "unix").writerow(data.values().__iter__())

					# Remove extra \n
					user_file.seek(user_file.tell() - 1, os.SEEK_SET)
					user_file.truncate()

					return True

		except IOError:
			return False

	def read_user(self, user_id: int) -> UserDataType:
		with self.parent.user_lockers.user_lock(user_id):
			with open(os.path.join(UserDataHandler._project_root, "data", "users", f"{user_id}.csv"), "r", newline = "") as user_file:
				return {
					key: value_cast(value)
					for key, value, value_cast in zip(
						UserDataType.__annotations__.keys(),
						csv.reader(user_file, "unix").__next__(),
						UserDataType.__annotations__.values()
					)
				}
"""