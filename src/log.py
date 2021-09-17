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
		self.data_log = os.path.join(LogHandler._log_root, "data.log")
		self.transation_log = os.path.join(LogHandler._log_root, "transation.log")

	def __write(self, to_what: str, what: str):
		acquired = False

		write_lock = fasteners.InterProcessReaderWriterLock(to_what)
		try:
			acquired = write_lock.acquire_write_lock()

			if acquired:
				with open(to_what, "a") as the_file:
					the_file.write(f"{_now_str}: {what}\n")

		finally:
			if acquired:
				write_lock.release_write_lock()

	def log_data_failure(self, object_type: str, object_id: int, object_data: Dict):
		self.__write(self.data_log, f"[F] {object_type}>{object_id} {dumps(object_data, separators = (',', ':'))}")

	def log_transation(self, from_id: int, to_id: int, amount: int):
		self.__write(self.transation_log, f"[T] {amount} credit{'' if amount == 1 else 's'} from {from_id} to {to_id}")
