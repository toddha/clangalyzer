import os
import time
from comparison import Comparison
from logger import Logger
from path_shortener import PathShortener
from timing_data_item import TimingDataItem
from typing import Dict, List, Optional, Set

class Context:
	'''The context contains a properties that are configurable and manages basic state of the build analysis.'''
	def __init__(self,
		output_path = None,
		folders = [],
		reveal = True,
		comparison_file_name = 'comparison.json',
		run_comparison = True,
		last_comparison_file_path = None,
		comparison_name = None,
		log = Logger(),
		targets = set(),
		detailed_analysis = True,
		path_shortener = PathShortener()):
		'''Initializes the context with specified settings.'''
		self._output_path = output_path
		self._log = log
		self._timing_data_items = []
		self._targets_to_timing_data_items = None
		
		self._run_comparison = run_comparison
		self._last_comparison = None
		self._last_comparison_file_path = last_comparison_file_path
		self._comparison_file_name = comparison_file_name
		self._comparison_name = comparison_name
		
		self._detailed_analysis = detailed_analysis
		self._folders = folders
		self._folders_deduped = False
		self._reveal = reveal
		self._path_shortener = path_shortener
		self._targets = targets
		return
	
	def initialize(self) -> None:
		'''
		Initializes the context for use.
		
		Must be called after all necessary properties are set in order to initialize everything appropriately.
		'''
		self._create_output_path()
		self._find_last_comparison()
		self._create_new_comparison()
		self._path_shortener.log_shortened_paths(self._log)
		return
	
	def should_reveal(self) -> bool:
		'''
		Returns whether or not the output path should be revealed after finishing the analysis.
		'''
		return self._reveal

	def has_output_path(self) -> bool:
		'''
		Whether or not there is an output path set.
		
		Empty string implies that there is no path.
		'''
		if self._output_path == "":
			self._output_path = None
		if self._output_path == None:
			return False
		return True
	
	def output_path(self) -> str:
		'''Returns the current output path. This is where analyzer data can be written.'''
		return self._output_path
	
	def set_output_path(self, output_path) -> None:
		'''Sets the output path. This is where analyzer data will be written.'''
		self._output_path = output_path
		return
	
	def _create_output_path(self) -> None:
		'''Creates the output path so that tools can be written.'''
		self._log.log("[Creating output path]")
		if not self.has_output_path():
			self._log.log_error_and_exit('No output path was specified.')
		
		if not os.path.exists(self._output_path):
			self._log.log_error_and_exit('Output path does not exist : %s' % self._output_path)
		
		folder_name = time.strftime("%Y-%m-%d-%H-%M-%S")
		self._output_path = os.path.join(self._output_path, folder_name)
		if os.path.exists(self._output_path):
			self._log.log_error_and_exit("Path %s already exists (are you running the script multiple times per second?)" % self._output_path)
		os.mkdir(self._output_path)
		self._log.log("Created output path at %s" % self._output_path)
		
		self._log.log()
		return
	
	def comparison_name(self) -> Optional[str]:
		'''
		Gets the comparison name (if set)
		'''
		return self._comparison_name
	
	def set_comparison_name(self, comparison_name: str) -> None:
		'''
		Sets the comparison name.
		'''
		self._comparison_name = comparison_name
	
	def _create_new_comparison(self) -> None:
		'''
		Creates the current comparison data for this run.
		'''
		self._comparison = Comparison(name=self._comparison_name, log=self._log)
		return
	
	def _find_last_comparison(self) -> None:
		'''
		Finds the last comparison, if any.
		
		The last comparison is used in order to track deltas against the current comparison.
		'''
		if not self._run_comparison:
			return
		
		self._log.log("[Loading last comparison data]")
		
		if self._last_comparison_file_path != None and os.path.isfile(self._last_comparison_file_path):
			self._log.log(f'Using comparison {self._last_comparison_file_path} ...')
			self._last_comparison = Comparison(log=self._log, name=None, filepath=self._last_comparison_file_path)
			self._log.log()
			return
		
		(search_path, _) = os.path.split(self._output_path)
		
		last_comparison_file_path = self._last_comparison_file_path
		if last_comparison_file_path != None and os.path.isdir(last_comparison_file_path):
			self._log.log(f'Inspecting directory {last_comparison_file_path} ...')
			
			# we support either specifying the parent analysis output directory or a specific analysis output directory
			comparison_file_path = os.path.join(last_comparison_file_path, self._comparison_file_name)
			if os.path.exists(comparison_file_path):
				# we were given a specific snapshot directory
				self._log.log('Specific comparison found inside of the directory')
				self._log.log(f'Using comparison {self._last_comparison_file_path} ...')
				self._last_comparison = Comparison(log=self._log, name=None, filepath=comparison_file_path)
				self._log.log()
				return
			
			self._log.log('Using given path as location to search for comparisons')
			search_path = last_comparison_file_path
			last_comparison_file_path = None
		
		self._log.log(f'Finding last comparison data in {search_path}')
		listing = os.listdir(search_path)
		listing.sort()
		listing.reverse()
		for item in listing:
			output_path = os.path.join(search_path, item)
			if output_path == self._output_path:
				continue
			if not os.path.isdir(output_path):
				# ignore files
				continue
			comparison_file_path = os.path.join(output_path, self._comparison_file_name)
			if not os.path.exists(comparison_file_path):
				# comparison file doesn't exist
				continue
			
			# load the comparison
			possible_comparison = Comparison(log=self._log, name=None, filepath=comparison_file_path)
			
			# pick the first one we find unless comparison name was specified
			matches_name = True
			if self._comparison_name != None:
				possible_comparison_name = possible_comparison.name()
				matches_name = possible_comparison_name == self._comparison_name
				
				if not matches_name:
					self._log.verbose(f'Skipping comparison, name "{possible_comparison_name}" does not match "{self._comparison_name}"')
					continue
				else:
					self._log.verbose(f'Matched name "{possible_comparison_name}" with "{self._comparison_name}"')
			
			self._log.log('Comparison data found')
			self._last_comparison = possible_comparison
			break
		
		if self._last_comparison == None:
			self._log.log('No comparison data found')
			self._log.log()
			return
		
		self._log.log()
		return
	
	def run_comparison(self) -> bool:
		'''Whether or not to run the comparison logic.'''
		return self._run_comparison
	
	def folders(self) -> List[str]:
		'''Returns the folders to analyze.'''
		self._dedupe_folders()
		return list(self._folders)
	
	def add_folder(self, folder: str) -> None:
		'''Adds the given folder to the list of folders to analyze.'''
		self._folders_deduped = False
		self._folders.append(folder)
		return
	
	def _dedupe_folders(self) -> None:
		'''Dedupes the folders to analyze, if necessarys. Does not work for case sensitive filesystems.'''
		if self._folders_deduped:
			return
		self._folders_deduped = True
		folders_set = set()
		new_folders = []
		for folder in self._folders:
			folder_lower = folder.lower()
			if not folder_lower in folders_set:
				new_folders.append(folder)
				folders_set.add(folder_lower)
		
		new_folders.sort()
		self._folders = new_folders
		if len(self._folders) > 0:
			for folder in self._folders:
				self._log.log(" -> %s" % folder)
			self._log.log()
		return
	
	def comparison_filename(self) -> str:
		'''Returns the comparison's filename'''
		return self._comparison_file_name
	
	def last_comparison(self) -> Comparison:
		'''Returns the last comparison, if any.'''
		return self._last_comparison
	
	def comparison(self) -> Comparison:
		'''Returns the current comparison.'''
		return self._comparison
	
	def has_targets(self) -> bool:
		'''Determines whether or not specific targets are specified.'''
		return len(self._targets) > 0
	
	def targets(self) -> Set[str]:
		'''Returns the set of targets specified by the user'''
		return set(self._targets)
	
	def log(self) -> Logger:
		'''Returns the Logger'''
		return self._log
	
	def set_timing_data_items(self, timing_data_items) -> None:
		'''Sets the current timing data items.'''
		self._timing_data_items = list(timing_data_items)
		self._targets_to_timing_data_items = None
		return
	
	def timing_data_items(self) -> List[TimingDataItem]:
		'''Returns a copy of the list of timing data items'''
		return list(self._timing_data_items)
	
	def timing_data_items_by_targets(self) -> Dict[str, List[TimingDataItem]]:
		'''Returns a dictionary containing all timing data items, sorted by targets.'''
		if self._targets_to_timing_data_items == None:
			self._targets_to_timing_data_items = {}
			for timing_item in self._timing_data_items:
				target = timing_item.get_target()
				if target not in self._targets_to_timing_data_items:
					self._targets_to_timing_data_items[target] = []
				self._targets_to_timing_data_items[target].append(timing_item)
		return dict(self._targets_to_timing_data_items)
	
	def is_detailed(self) -> bool:
		'''Whether or not detailed analysis is on.'''
		return self._detailed_analysis
	
	def path_shortener(self) -> PathShortener:
		'''Returns the path shortener'''
		return self._path_shortener
	
	def get_known_timing_data_item_suffixes_to_skip(self) -> Set[str]:
		'''
		Returns a set of filename suffixes which should not be inspected as they are not timing data items
		
		Certain JSON files we know are invalid because they are generated by Xcode
		'''
		return set([
			'-outputfilemap.json',
			'-buildrequest.json',
		])
		

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
