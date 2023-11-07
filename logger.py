import os
import sys
import time

# This class just logs.
class Logger:
	def __init__(self, quiet_output = False, verbose = False):
		self._verbose = verbose
		self._quiet_output = quiet_output
		self._internal_lines = []
		self._last_finished = True
		self._last_output_time = 0
		if self._can_output_colors():
			self.color_light_grey = '\033[37m'
			self.color_dark_grey = '\033[90m'
			self.color_red = '\033[91m'
			self.color_green = '\033[92m'
			self.color_yellow = '\033[93m'
			self.color_blue = '\033[94m'
			self.color_purple = '\033[95m'
			self.color_cyan = '\033[96m'
			self.color_clear = '\033[0m'
		else:
			self.color_light_grey = ''
			self.color_dark_grey = ''
			self.color_red = ''
			self.color_green = ''
			self.color_yellow = ''
			self.color_blue = ''
			self.color_purple = ''
			self.color_cyan = ''
			self.color_clear = ''
		return
	
	def _decolorize_text(self, message) -> str:
		if self._can_output_colors():
			message = message.replace(self.color_light_grey, '')
			message = message.replace(self.color_dark_grey, '')
			message = message.replace(self.color_red, '')
			message = message.replace(self.color_green, '')
			message = message.replace(self.color_yellow, '')
			message = message.replace(self.color_blue, '')
			message = message.replace(self.color_purple, '')
			message = message.replace(self.color_cyan, '')
			message = message.replace(self.color_clear, '')
		return message
	
	def _can_output_colors(self):
		if sys.stdout.isatty():
			term_key = 'TERM'
			if term_key in os.environ:
				term = os.environ[term_key]
				return term == 'xterm-256color'
		return False
	
	def log_warning(self, message):
		self.log('%s %s' % (self.colorize('WARNING:', self.color_yellow), message))
		return
	
	def log_verbose_warning(self, message):
		if self._verbose:
			self.log_warning(message)
		return
	
	def log_error_and_exit(self, message):
		self.log()
		self.log('%s %s' % (self.colorize('ERROR:', self.color_red), message))
		sys.exit(1)
	
	def log(self, message="", finished=True, force_print=False) -> None:
		self.log_internal(message, finished, should_print = True, force_print = force_print)
		return
	
	def log_internal(self, message, finished, should_print, force_print = False) -> None:
		if self._quiet_output:
			should_print = False
		# TODO :handle force_print
		#if force_print:
		#	should_print = True
		message_with_time = "%s %s" % (time.strftime("[%Y-%m-%d %H:%M:%S] ", time.localtime()), message)
		if not self._last_finished:
			self._internal_lines.pop()
			if should_print:
				if sys.stdout.isatty():
					# magic to erase the line and move the cursor to the beginning
					sys.stdout.write('\033[2K\033[1G')
					sys.stdout.flush()
				else:
					print()
		self._internal_lines.append(message_with_time)
		if should_print:
			self._last_finished = finished
			if not finished:
				print(message_with_time.strip(), end=" ")
				sys.stdout.flush()
			else:
				print(message_with_time.strip())
		return
	
	def log_partial_status(self, message="", check_last_time=False):
		n = int(time.time())
		if check_last_time:
			if self._last_output_time == n:
				return
		self._last_output_time = n
		self.log_internal(message, finished=False, should_print=True)
		return
	
	def is_verbose(self) -> bool:
		return self._verbose
	
	def verbose(self, message=""):
		self.log_internal(message, True, self._verbose)
		return
	
	def colorize(self, string, color):
		return '%s%s%s' % (color, string, self.color_clear)
	
	def write_to_file(self, file) -> None:
		for line in self._internal_lines:
			file.write(self._decolorize_text(line))
			file.write('\n')
		return



if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
