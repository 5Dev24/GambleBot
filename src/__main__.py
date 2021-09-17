#!/usr/bin/env python3

from pathlib import Path
import asyncio
import dotenv
import gamble
import data
import time
import os

async def _cache_cleanup(bot: gamble.GambleBot):
	await asyncio.sleep(10)

	while True:
		now = int(time.time())
		for cache_name in list(bot.data._cache.keys()):
			for object_id in list(bot.data._cache[cache_name].keys()):
				if bot.data._cache[cache_name][object_id]["last_access"] + 600 < now:
					del bot.data._cache[cache_name][object_id]

		# Purge rate limit too

		await asyncio.sleep(60)

def main():
	# Must setup bath for data handler so it can locate data files
	_project_root = Path(os.path.abspath(__file__)).parent.parent.__str__()
	data.DataHandler._project_root = _project_root

	# Make sure the folders exist
	os.makedirs(os.path.join(_project_root, "data", "users"), 0o744, True)
	os.makedirs(os.path.join(_project_root, "data", "guilds"), 0o744, True)

	dotenv.load_dotenv()
	bot = gamble.GambleBot()

	asyncio.create_task(_cache_cleanup())

	bot.run(os.getenv("ClientSecret"))

if __name__ == "__main__": main()