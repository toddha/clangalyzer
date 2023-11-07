from enum import Enum
import json
from typing import Dict, Optional

import utils.truncation
from logger import Logger

class ComparisonOutputType(Enum):
	'''Defines how a given data type should be output'''
	
	NUMBER = 0
	''' A number. No additional formatting supplied.'''

	TIME_MILLISECONDS = 1
	''' Time. Will output in ms or seconds.'''

	TIME_CPU_SECONDS = 2,
	''' Time. Will output in seconds.'''

	FILESIZE = 3
	''' File size. Will output in bytes, KB, MB, GB.'''

	@staticmethod
	def type_to_string(outputType) -> str:
		if outputType == ComparisonOutputType.NUMBER:
			return ""
		elif outputType == ComparisonOutputType.TIME_CPU_SECONDS:
			return "CPU seconds"
		elif outputType == ComparisonOutputType.TIME_MILLISECONDS:
			return "ms"
		elif outputType == ComparisonOutputType.FILESIZE:
			return "bytes"
		
		raise AssertionError("type not implemented")

	@staticmethod
	def _filesize_to_shortened_string(value: float, suffix: str) -> str:
		'''
		Converts the filesize to a shortened string
		
		If value < 10, then we'll display something like 1.23 [suffix]
		If value < 100, then we'll display something like 19.2 [suffix]
		Otherwise just 354 [suffix]
		'''
		if value < 10:
			return "%0.2f %s" % (value, suffix)
		elif value < 100:
			return "%0.1f %s" % (value, suffix)
		return "%d %s" % (value, suffix)
	
	@staticmethod
	def value_to_string(outputType, value: int) -> str:
		'''Converts the specified value with the given outputType to the output string'''
		if value == 0:
			return "-"
		
		if outputType == ComparisonOutputType.NUMBER:
			return str(value)
		elif outputType == ComparisonOutputType.TIME_CPU_SECONDS:
			return "%0.2f sec" % float(value)
		elif outputType == ComparisonOutputType.TIME_MILLISECONDS:
			if value < 1000:
				return str(value) + "ms"
			seconds = float(value) / 1000
			return "%0.2f sec" % seconds
		elif outputType == ComparisonOutputType.FILESIZE:
			if value < 1024:
				return str(value) + " bytes"
			kb = float(value) / 1024
			if kb < 1024:
				return ComparisonOutputType._filesize_to_shortened_string(kb, "KB")
			mb = float(kb) / 1024
			if mb < 1024:
				return ComparisonOutputType._filesize_to_shortened_string(mb, "MB")
			gb = float(mb) / 1024
			return ComparisonOutputType._filesize_to_shortened_string(gb, "GB")

		raise AssertionError("type not implemented")

class Comparison:
	'''
	Contains all comparison data for a given analysis run.
	
	This class is updated by individual tools; it should be the highlights of what you are comparing from analysis run to analysis run.
	'''
	def __init__(self, log: Logger, filepath: Optional[str] = None, name: Optional[str] = None):
		'''
		Initializes the comparison with the given filepath or given name.
		
		If filepath is specified, it will decode the JSON from the given comparison.
		If filepath is not specified, it must pass the name and will create an empty comparison.
		'''
		self._name_key = "*** Name ***"
		if filepath == None:
			self._dict = {}
			self._set_name(name = name, log = log)
		else:
			if log == None:
				raise AssertionError('log must be passed if passing filepath')
			assert log is not None
			assert filepath is not None
			log.verbose(f'Reading comparison data from {filepath}...')
			with open(filepath, 'r') as f:
				text = f.read()
			log.verbose(f'Decoding comparison data...')
			self._dict = json.JSONDecoder().decode(text)
		return
	
	def _set_name(self, name: Optional[str], log: Logger) -> None:
		'''
		Sets the name for the comparison if one is specified.
		
		If name is not specified, will use empty string.
		'''
		if name == None:
			name = ""
		
		self._dict[self._name_key] = name
		return
	
	def name(self) -> str:
		'''
		Gets the name for the comparison.
		
		If one is not specified, will pass back empty string.
		'''
		name = ""
		if self._name_key in self._dict:
			name = self._dict[self._name_key]
		return name
	
	def add_summary(self, log, name, dict) -> None:
		'''Adds the summary data to the comparison with the given name. The name must not already exist (each caller must give a unique key).'''
		if name in self._dict:
			log.log_error_and_exit(f'Comparison summary data for {name} already exists. Names must be unique as well as only added once.')
		self._dict[name] = dict
		return
	
	def write_to_file(self, file) -> None:
		'''Writes the summary data to the given file.'''
		json_text = json.JSONEncoder(sort_keys=True, indent=4, separators=(',', ': ')).encode(self._dict)
		file.write(json_text + '\n\n')
		return
	
	def summary_data(self, log, name) -> Dict:
		'''Returns the summary data from the comparison for the given name.
		
		If the name does not exist, it will return an empty dictionary.
		'''
		if not name in self._dict:
			log.log('No comparison data could be loaded')
			return {}
		return self._dict[name]

	@staticmethod
	def log_summary(key: str, units: ComparisonOutputType, summary: Dict, last_summary: Dict, log: Logger, smaller_is_better=True) -> None:
		'''Logs the summary data to the specified logger.'''
		clear_color = log.color_clear
		if smaller_is_better:
			(smaller_color, bigger_color, no_difference_color) = (log.color_green, log.color_red, log.color_light_grey)
		else:
			(smaller_color, bigger_color, no_difference_color) = (log.color_red, log.color_green, log.color_light_grey)
		
		log.log(f'* {key}')
		log.log('%16s %16s %16s   %s' % ('Last', 'Current', 'Delta', 'Name'))
		keys_set = set(summary.keys())
		keys_set = keys_set.union(set(last_summary.keys()))
		keys = list(keys_set)
		keys.sort()
		for key in keys:
			last_value = None
			last_value_string = "-"
			if key in last_summary:
				last_value = last_summary[key]
				last_value_string = ComparisonOutputType.value_to_string(units, last_value)
			
			value = None
			value_string = "-"
			if key in summary:
				value = summary[key]
				value_string = ComparisonOutputType.value_to_string(units, value)
			
			if last_value == None or value == None or last_value == 0 and value == 0:
				difference = "n/a"
				color = no_difference_color
			else:
				assert last_value is not None
				assert value is not None
				
				# ensure we have a leading symbol if positive and calculate colors
				plus_or_none = ''
				color = no_difference_color
				if value < last_value:
					plus_or_none = '+'
					color = smaller_color
				elif value > last_value:
					color = bigger_color
				
				# determine difference string
				if last_value > 0:
					percentage = ((last_value - value) / last_value) * 100
					if (percentage >= 100 or percentage <= -100) :
						percentage = int(percentage)
						difference = '%s%d%%' % (plus_or_none, percentage)
					else:
						difference = '%s%0.2f%%' % (plus_or_none, utils.truncation.truncate_to_place(percentage, 2))
				else:
					difference = '%s∞%%' % (plus_or_none)
			
			difference = '%16s %16s %s%16s%s   %s' % (last_value_string, value_string, color, difference, clear_color, key)
			log.log(difference)
		return


if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
