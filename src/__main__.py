#!/usr/bin/env python3

from posixpath import expanduser
from discord import user
from discord.ext import tasks
from pathlib import Path
import asyncio
import dotenv
import gamble
import data
import time
import log
import os

def main():
	# Must setup bath for data handler so it can locate data files
	_project_root = Path(os.path.abspath(__file__)).parent.parent.__str__()
	data.DataHandler._data_root = os.path.join(_project_root, "data")
	log.LogHandler._log_root = os.path.join(_project_root, "logs")

	# Make sure the folders exist
	os.makedirs(os.path.join(_project_root, "data", "users"), 0o744, True)
	os.makedirs(os.path.join(_project_root, "data", "guilds"), 0o744, True)
	os.makedirs(os.path.join(_project_root, "logs"), 0o744, True)

	dotenv.load_dotenv()
	bot = gamble.GambleBot()

	@tasks.loop()
	async def cache_cleanup():
		purge_time = 600
		wait_time = 60

		await asyncio.sleep(10)

		while True:
			now = int(time.time())
			for cache_name in list(bot.data._cache.keys()):
				for object_id in list(bot.data._cache[cache_name].keys()):
					if bot.data._cache[cache_name][object_id]["last_access"] + purge_time < now:
						print("Purging", object_id, "from", cache_name, "cache")
						del bot.data._cache[cache_name][object_id]

			for user_id in list(bot.command_handler.rate_limit.keys()):
				if bot.command_handler.rate_limit[user_id] + purge_time < now:
					print("Purging", user_id, "from rate limit cache")
					try:
						del bot.command_handler.rate_limit[user_id]
						del bot.command_handler.rate_limit_locks[user_id]
					except KeyError:
						pass

			await asyncio.sleep(wait_time)

	cache_cleanup.start()

	bot.run(os.getenv("ClientSecret"))

if __name__ == "__main__":
	main()
