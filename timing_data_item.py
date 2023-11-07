from logger import Logger
from typing import Dict

class TimingDataItem:
	'''This class represents a single JSON item from the timing data'''
	def __init__(self, filename, target, arch, platform) -> None:
		self._filename = filename
		self._target = target
		self._arch = arch
		self._platform = platform
		self._duration = 0
		self._key_item_timestamp = "ts"
		self._key_item_duration = "dur"
		self._key_item_process_identifier = "pid"
		self._key_item_thread_identifier = "tid"
		self._key_name = "name"
		return
	
	def is_total(self) -> bool:
		'''Returns whether or not the item is a "Total " item'''
		return self.get_name().startswith("Total ")

	def is_total_execute_compiler(self) -> bool:
		'''Returns whether or not the item is "Total ExecuteCompiler"'''
		return self.get_name() == "Total ExecuteCompiler"
	
	def is_codegen_function(self) -> bool:
		'''Returns whether or not the item is "CodeGen Function"'''
		return self.get_name() == "CodeGen Function"

	def is_source(self) -> bool:
		'''Returns whether or not the item is "Source"'''
		return self.get_name() == "Source"
	
	def is_execute_compiler(self) -> bool:
		'''Returns whether or not the item is "ExecuteCompiler"'''
		return self.get_name() == "ExecuteCompiler"

	def get_short_total_name(self) -> str:
		'''Returns the short name for the total item. Empty if not a total item'''
		if not self.is_total():
			return ""
		return self.get_name()[len("Total "):]

	def get_duration(self) -> int:
		'''Returns the duration of the item in nanoseconds'''
		return self._duration
	
	def get_total_time(self) -> int:
		'''Returns the total time of the item'''
		return self.time + self._duration
	
	def get_detail(self) -> str:
		'''Returns the detail, if present. Otherwise empty string.'''
		detail = ""
		key_args = "args"
		if key_args in self._dict:
			key_detail = "detail"
			if key_detail in self._dict[key_args]:
				detail = self._dict[key_args][key_detail]
		return detail
	
	def get_filename(self) -> str:
		'''Returns the filename of the item.'''
		return self._filename

	def get_arch(self) -> str:
		'''Returns the architecture the item targeted.'''
		return self._arch

	def get_platform(self) -> str:
		'''Returns the platform the item targeted.'''
		return self._platform

	def get_target(self) -> str:
		'''Returns the source target for item.'''
		return self._target
	
	def get_name(self) -> str:
		'''Returns the name of the item. Empty if not present.'''
		name = ""
		if self._key_name in self._dict:
			name = self._dict[self._key_name]
		return name
	
	def _read_int_from_dict(self, key: str, log: Logger) -> int:
		'''Reads the key as an int from the dictionary.'''
		if key not in self._dict:
			log.log_error_and_exit("Could not find key %s in item : %s" % (key, str(self._dict)))
		
		string_value = self._dict[key]
		try:
			value = int(string_value)
		except:
			log.log_error_and_exit("%s string was invalid : %s" % (key, string_value))
		return value
	
	def parse(self, item_dict, log) -> bool:
		'''Parse the item dictionary and shred values.'''
		self._dict = item_dict
		
		self.time = self._read_int_from_dict(self._key_item_timestamp, log)
		self.pid = self._read_int_from_dict(self._key_item_process_identifier, log)
		self.tid = self._read_int_from_dict(self._key_item_thread_identifier, log)
		
		if self._key_item_duration in self._dict:
			self._duration = self._read_int_from_dict(self._key_item_duration, log)
		
		return True
	
	def json_dict(self) -> Dict:
		'''Returns the specified dictionary as a JSON dictionary.'''
		d = {}
		for (k, v) in self._dict.items():
			d[k] = v
		
		# change the name from ExecuteCompiler to include the filename
		name = self.get_name()
		if self.is_execute_compiler():
			name = "%s - %s" % (name, self._filename)
			d[self._key_name] = name
		
		# we modify the some keys, like pid, tid, time
		d[self._key_item_timestamp] = self.time
		d[self._key_item_process_identifier] = self.pid
		d[self._key_item_thread_identifier] = self.tid
		
		return d

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')