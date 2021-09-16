#!/usr/bin/env python3

from pathlib import Path
import dotenv
import gamble
import data
import os

def main():
	# Must setup bath for data handler so it can locate data files
	_project_root = Path(os.path.abspath(__file__)).parent.parent.__str__()
	data.DataHandler._project_root = _project_root

	# Make sure the folders exist
	os.makedirs(os.path.join(_project_root, "data", "users"), 0o744, True)
	os.makedirs(os.path.join(_project_root, "data", "guilds"), 0o744, True)

	dotenv.load_dotenv()
	gamble.GambleBot().run(os.getenv("ClientSecret"))

if __name__ == "__main__": main()