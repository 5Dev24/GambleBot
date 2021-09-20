from typing import Dict
from json import dumps
import fasteners
import datetime
import os

def _now_str() -> str:
	return datetime.datetime.now().strftime("< %d/%m/%Y - %H:%M:%S >")

class LogHandler:

	_log_root: str = None # Set at runtime in __main__

	def __init__(self):
		self.master_log = os.path.join(LogHandler._log_root, "master.log")
		self.data_log = os.path.join(LogHandler._log_root, "data.log")
		self.transations_log = os.path.join(LogHandler._log_root, "transations.log")
		self.gains_log = os.path.join(LogHandler._log_root, "gains.log")
		self.losses_log = os.path.join(LogHandler._log_root, "losses.log")

	def __write(self, to_what: str, what: str): # Future updates should make this a queue system
		acquired = False

		write_lock = fasteners.InterProcessReaderWriterLock(to_what)
		try:
			acquired = write_lock.acquire_write_lock()

			if acquired:
				with open(to_what, "a") as the_file:
					the_file.write(f"{_now_str()} {what}\n")

		finally:
			if acquired:
				write_lock.release_write_lock()

	def log_data_failure(self, object_type: str, object_id: int, source: str, object_data: Dict):
		self.__write(self.master_log, f"[F] {object_type}>{object_id}, {source} couldn't save {dumps(object_data, separators = (',', ':'))}")
		self.__write(self.data_log, f"{object_type}>{object_id}, {source} couldn't save {dumps(object_data, separators = (',', ':'))}")

	def log_transation(self, from_id: int, to_id: int, amount: int):
		self.__write(self.master_log, f"[T] {amount} credit{'' if amount.__abs__() == 1 else 's'} from {from_id} to {to_id}")
		self.__write(self.transations_log, f"{amount} credit{'' if amount.__abs__() == 1 else 's'} from {from_id} to {to_id}")

	def log_gain(self, user_id: int, amount: int, source: str):
		self.__write(self.master_log, f"[G] {user_id} gained {amount} credit{'' if amount.__abs__() == 1 else 's'} from {source}")
		self.__write(self.gains_log, f"{user_id} gained {amount} credit{'' if amount.__abs__() == 1 else 's'} from {source}")

	def log_loss(self, user_id: int, amount: int, source: str):
		self.__write(self.master_log, f"[L] {user_id} loss {amount} credit{'' if amount.__abs__() == 1 else 's'} from {source}")
		self.__write(self.losses_log, f"{user_id} loss {amount} credit{'' if amount.__abs__() == 1 else 's'} from {source}")