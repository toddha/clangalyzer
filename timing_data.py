import json
import os
from pathlib import Path
import subprocess
from io import StringIO
from typing import List, Optional, Tuple

from logger import Logger
from path_shortener import PathShortener
from timing_data_item import TimingDataItem

class TimingData:
	'''
	This class represents a the entire compiler profile of a single source file.
	
	It contains mutliple timing data items - each was a task that the compiler emitted.
	'''
	@staticmethod
	def target_and_platform_and_arch_from_path(path) -> Optional[Tuple[str, str, str]]:
		'''Rips the target, platform, and architecture from the given path.'''
		# [ignored] rip the filename from the path
		(working_path, _) = os.path.split(path)
		
		# parent directory should be arch
		(working_path, arch) = os.path.split(working_path)
		
		# [ignored] parent directory should be "objects-normal-asan (dependent on build settings)"
		(working_path, _) = os.path.split(working_path)
		
		# parent directory should be target (ends in .build)
		(working_path, target) = os.path.split(working_path)
		build_suffix = ".build"
		if target.endswith(build_suffix):
			target = target[:(len(target) - len(build_suffix))]
			# parent directory should be platform
			(_, platform) = os.path.split(working_path)
		elif target == "SharedPrecompiledHeaders":
			arch = "-"
			platform = "-"
		else:
			return None
		
		return (target, platform, arch)
	
	def __init__(self, path: str, target: str, platform: str, arch: str) -> None:
		'''Initializes the timing data'''
		self._time_offset = 0
		self._key_trace_events = "traceEvents"
		self._key_beginning_of_time = "beginningOfTime"
		self._path = path
		self._items: List[TimingDataItem] = []
		self._target = target
		self._platform = platform
		self._arch = arch
		return
	
	def get_items(self) -> List[TimingDataItem]:
		'''Returns the list of timing data items associated with this timing data.'''
		return self._items
	
	def get_arch(self) -> str:
		'''Returns the architecture associated with this timing data.'''
		return self._arch
	
	def get_platform(self) -> str:
		'''Returns the platform associated with this timing data.'''
		return self._platform
	
	def get_target(self) -> str:
		'''Returns the target associated with this timing data.'''
		return self._target
	
	def get_path(self) -> str:
		'''
		Returns the path associated with this timing data.
		
		This is the path of the raw timing data emitted by the compiler, NOT the source file compiled
		'''
		return self._path
	
	def get_name(self) -> str:
		'''Returns the filename of the timing data that this instance represents.'''
		return os.path.basename(self.get_path())
	
	def parse(self, log) -> bool:
		'''Parses the timing data, and returns success or failure.'''
		name = os.path.basename(self._path)
		log.log_partial_status("Reading %s" % name)
		with open(self._path, 'rb') as f:
			try:
				json_text = f.read().decode('utf-8')
			except:
				log.log_warning("Could not read %s" % self._path)
				return False
		try:
			data = json.loads(json_text)
		except:
			log.log_verbose_warning("Could not load the json in %s" % self._path)
			return False
		
		log.log_partial_status("Processing %s" % name.strip())
		keys = [self._key_beginning_of_time, self._key_trace_events]
		for key in keys:
			if not key in data:
				log.log_verbose_warning("Could not find %s in %s" % (key, self._path))
				return False
		
		if len(data.keys()) != len(keys):
			log.log_warning("JSON in %s had unknown set of keys : %s" % (self._path, str(data.keys())))
			return False
		
		items = data[self._key_trace_events]
		for item in items:
			tdi = TimingDataItem(name, self._target, self._arch, self._platform)
			if tdi.parse(item, log):
				self._items.append(tdi)
		
		return True
	
	def join(self, other_timing_data, log: Logger) -> None:
		'''
		Combines the contents of another TimingDataItem into this one.
		
		Used primarily for serializing timing data. PID and TID will not be maintained.
		'''
		# go through all items, offset by the time offset, and add them
		other_items = other_timing_data._items
		
		pid: Optional[int] = None
		tid: Optional[int] = None
		if len(self._items) > 0:
			pid = self._items[0].pid
			tid = self._items[0].tid
		
		last_time = 0
		for other_item in other_items:
			if other_item.is_total_execute_compiler():
				last_time = other_item.get_total_time()
			other_item.time = other_item.time + self._time_offset
			
			# make sure we have the same pid and tid
			if pid == None:
				pid = other_item.pid
			else:
				assert pid is not None
				other_item.pid = pid
			if tid == None:
				tid = other_item.tid
			else:
				assert tid is not None
				other_item.tid = tid
			
			self._items.append(other_item)
		
		self._time_offset = self._time_offset + last_time
		return
	
	def calculate_total_time(self, log: Logger) -> int:
		'''Calculates the total time that this timing data instance took.'''
		if self._time_offset == 0:
			for item in self._items:
				if item.is_total_execute_compiler():
					if self._time_offset != 0:
						log.log_error_and_exit("found multiple execute compiler items")
					self._time_offset = item.get_total_time()
		return self._time_offset
	
	def get_total_time(self) -> int:
		'''
		Returns the total time that this timing data instance took.
		
		Only works if already calculated (either via joining, or explicitly calculating.)
		'''
		return self._time_offset

	def _shorten_paths_if_needed(self, str_value: str, path_shortener: PathShortener, log: Logger) -> str:
		'''Shortens the paths in the serialized JSON if need be'''
		paths_to_shorten = path_shortener.shortened_paths()
		if len(paths_to_shorten) > 0:
			log.verbose("pre-shortened JSON is %d long" % len(str_value))
			log.log("Shortening known paths...")
			for (k, v) in paths_to_shorten.items():
				str_value = str_value.replace(k, v)
			
			log.verbose("shortened JSON is %d long" % len(str_value))
		return str_value

	def write(self, path_shortener: PathShortener, log: Logger) -> bool:
		'''Serializes the timing data to a string and writes it to the current path. Returns success.'''
		io = StringIO()
		
		items = []
		i = 1
		j = len(self._items)
		if j == 0:
			log.log_warning("No items to serialize")
			return True
		
		for item in self._items:
			log.log_partial_status("Building object graph (%d of %d)..." % (i, j), check_last_time=True)
			i = i + 1
			d = item.json_dict()
			items.append(d)
		log.log("Built object graph (%d items)" % j)
		
		log.log_partial_status("Serializing JSON...")
		json_dict = { self._key_trace_events : items}
		json.dump(json_dict, io, indent=1)
		str_value = io.getvalue()
		log.log("Serialized JSON...")

		str_value = self._shorten_paths_if_needed(str_value, path_shortener, log)

		log.log_partial_status("Writing to %s" % os.path.basename(self._path))
		with open(self._path, 'w') as f:
			try:
				f.write(str_value)
			except:
				log.log_warning("Could not write to %s" % self._path)
				return False
		log.log("Wrote to %s" % self._path)
		return True

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
