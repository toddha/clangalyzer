import argparse
import os
import subprocess
from typing import Dict

from logger import Logger

class PathShortener:
	class keyvalue(argparse.Action):
		'''Helper class to do key value pairs'''
		def __call__( self , parser, namespace, values, option_string = None):
			for value in values:
				k, v = value.split('=')
				getattr(namespace, self.dest)[k] = v
	
	def __init__(self, shorten = True, paths = {}):
		self._shorten = shorten
		self._paths = paths
		return
	
	@staticmethod
	def add_parser_arguments(parser: argparse.ArgumentParser):
		'''Adds the default arguments to the parser.'''
		parser.add_argument(
			'--no-shorten-paths',
			dest='shorten',
			action='store_false',
			default=True,
			required=False,
			help='Turns off path shortening paths.')
		parser.add_argument(
			'--short-path',
			dest='short_paths',
			default={},
			nargs='*',
			action=PathShortener.keyvalue,
			required=False,
			help='Adds the known path so it can be shortened.')
		return
	
	@staticmethod
	def shortener_from_args(log : Logger, args : argparse.Namespace):
		'''Builds the PathShortener from the argument parser arguments.'''
		path_shortener = PathShortener(
			shorten = args.shorten,
		)
		
		# use the add_shortened_path in order to also go through log and checks
		for (k, v) in args.short_paths.items():
			path_shortener.add_shortened_path(log, k, v)
		return path_shortener
	
	def log_shortened_paths(self, log: Logger) -> None:
		'''Logs what the shortened paths are'''
		if self._shorten:
			log.log('[Paths shortened]')
			for (k, v) in self._paths.items():
				log.log("%s -> %s" % (k, v))
			log.log()
		return
	
	def add_xcode_paths(self, log: Logger) -> None:
		'''Adds the default Xcode paths too the path shortener'''
		xcode_path = self._determine_xcode_path(log)
		self.add_shortened_path(log, os.path.join(xcode_path, "Toolchains/XcodeDefault.xctoolchain"), "xcode_toolchain")
		self.add_shortened_path(log, os.path.join(xcode_path, "Platforms/MacOSX.platform/Developer/SDKs"), "macOS_SDK")
		self.add_shortened_path(log, os.path.join(xcode_path, "Platforms/iPhoneSimulator.platform/Developer/SDKs"), "iOS_SDK")
		return

	def add_shortened_path(self, log: Logger, long_path: str, shortened_name: str) -> bool:
		'''Adds the shortened path. Returns true if added, false if the long path was already shortened'''
		if long_path in self._paths:
			log.log_warning('shortened path %s already exists (tried %s, existing %s)' % (long_path, shortened_name, self._paths[long_path]))
			return False
		self._paths[long_path] = shortened_name
		return True

	def will_shorten(self) -> bool:
		'''Returns whether or not any paths will be shortened'''
		return self._shorten

	def shortened_paths(self) -> Dict[str, str]:
		'''Returns a copy of the shortened paths'''
		if not self._shorten:
			return {}
		return dict(self._paths)

	def shorten_path(self, path) -> str:
		'''
		Shortens the given path if necessary
		
		If there are multiple paths found (i.e. /foo -> f and /foo/bar -> fb),
		the path shortening will find the shortest resulting path.
		'''
		if not self._shorten:
			return path
		best_path = path
		for (k, v) in self._paths.items():
			if path.startswith(k):
				replaced_path = path.replace(k, v)
				if len(replaced_path) < len(best_path):
					best_path = replaced_path
		return best_path
	
	def _determine_xcode_path(self, log: Logger) -> str:
		'''
		Determines via xcode-select where Xcode is installed.
		
		If fails, assumes in /Applications.
		'''
		log.log_partial_status("Determining Xcode version...")
		try:
			xcode_path = subprocess.run(["/usr/bin/xcode-select", "-p"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode('utf-8').strip()
			log.log(f'Determined Xcode at {xcode_path}')
		except:
			xcode_path = "/Applications/Xcode.app/Contents/Developer"
			log.log(f'Failed to run xcode-select, assuming at {xcode_path}')
		return xcode_path

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
