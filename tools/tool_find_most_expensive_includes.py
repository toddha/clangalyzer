import os
from comparison import Comparison
from logger import Logger
from tool import Tool
from timing_data_item import TimingDataItem
from typing import Dict, List, Set, Tuple

class ToolFindMostExpensiveIncludes(Tool):
	def __init__(self):
		self._empty_target_name = ""
		return
	
	def name(self) -> str:
		return 'Expensive Includes'
	
	def description(self) -> str:
		return 'Outputs the summaries of which files are included by the compilation process and \
				how long they take in aggregate.'
	
	def add_arguments(self, parser) -> None:
		parser.add_argument(
			'--no-tool-find-expensive-includes',
			dest='tool_find_expensive_includes',
			action='store_false',
			default=True,
			required=False,
			help='Turns off running the tool which finds the most expensive includes.')
		return
	
	def process_arguments(self, args) -> None:
		self._enabled = args.tool_find_expensive_includes
		return
	
	def run(self, context):
		log = context.log()
		targets: Dict[str, Dict[str, Tuple[str, int, int, List[TimingDataItem]]]] = {}
		targets_to_source_files: Dict[str, Set[str]] = {}

		timing_items = context.timing_data_items()
		for timing_item in timing_items:
			log.log_partial_status("Inspecting %s"  % timing_item.get_name())
			
			# figure out total count for targets
			# use the full path of the item - not the filename, since filenames may not be unique
			target_name = timing_item.get_target()
			if target_name not in targets_to_source_files:
				targets_to_source_files[target_name] = set()
			targets_to_source_files[target_name].add(timing_item.get_path())
			
			items = timing_item.get_items()
			for item in items:
				if not item.is_source():
					continue
				source_file = item.get_detail()
				if len(source_file) == 0:
					log.log_warning("no source file associated with source item")
					continue
				target_name = item.get_target()
				if len(target_name) == 0:
					log.log_warning("no target associated with source item")
					continue
				
				# add the source item twice - once for the project (i.e. empty target name), once for the individual target
				targets = self._add_item_to_source_files(self._empty_target_name, targets, source_file, item)
				targets = self._add_item_to_source_files(target_name, targets, source_file, item)
		
		include_count = 0
		if self._empty_target_name in targets:
			sources_files = targets[self._empty_target_name]
			include_count = len(sources_files)
		if include_count == 0:
			log.log_warning("No includes were founds")
			return
			
		log.log("Found %d includes" % include_count)
		output_path = context.output_path()
		detailed = context.is_detailed()
		if not self._write_expensive_includes_sorted_by_time(log, output_path, targets, detailed, sort_by_target=False, ignore_single_includes=False, targets_to_source_files=targets_to_source_files):
			return False
		if not self._write_expensive_includes_sorted_by_time(log, output_path, targets, detailed, sort_by_target=True, ignore_single_includes=True, targets_to_source_files=targets_to_source_files):
			return False
		if not self._write_expensive_includes_sorted_by_file(log, output_path, targets):
			return False
		return True
	
	def _add_item_to_source_files(self, target_name: str, targets: Dict[str, Dict[str, Tuple[str, int, int, List[TimingDataItem]]]], source_file: str, item: TimingDataItem) -> Dict[str, Dict[str, Tuple[str, int, int, List[TimingDataItem]]]]:
		'''
		Adds the timing data item to the targets dictionary

		The targets dictionary is keyed by the target_name and we get back out another dictionary.
		
		That dictionary is keyed by the source file name (lowercased) and contains a tuple.
		
		This tuple contains :
		- the source file actual name (not lowercased)
		- the total duration for the source file (i.e. total time that file spent being included)
		- the number of times that file was include
		- the list of all of the timing data items which were accounted for
		'''
		source_files: Dict[str, Tuple[str, int, int, List[TimingDataItem]]] = {}
		if target_name in targets:
			source_files = targets[target_name]
		
		source_file_value = 0
		count = 0
		items: List[TimingDataItem] = []
		
		source_file_key = source_file.lower()
		if source_file_key in source_files:
			(source_file, source_file_value, count, items) = source_files[source_file_key]
		items.append(item)
		source_files[source_file_key] = (source_file, source_file_value + item.get_duration(), count + 1, items)
		targets[target_name] = source_files
		return targets
	
	def _write_expensive_includes_sorted_by_time(self, log: Logger, working_path: str, targets: Dict[str, Dict[str, Tuple[str, int, int, List[TimingDataItem]]]], detailed: bool, sort_by_target: bool, ignore_single_includes: bool, targets_to_source_files: Dict[str, Set[str]]) -> bool:
		'''
		Writes the expensive includes, sorted by time.
		'''
		file_name = "expensive_includes.txt"
		if sort_by_target:
			file_name = "expensive_includes_by_target.txt"
		
		most_expensive_includes_path = os.path.join(working_path, file_name)
		log.log_partial_status("Writing summary file sorted by time...")
		
		with open(most_expensive_includes_path, 'w') as f:
			try:
				total_items_in_target = 0
				if sort_by_target:
					target_names = list(targets.keys())
					target_names.remove(self._empty_target_name)
					target_names.sort()
				else:
					target_names = [self._empty_target_name]
					for (_, v) in targets_to_source_files.items():
						total_items_in_target += len(v)

				for target_name in target_names:
					f.write("\n\n>>>>> %s\n\n" % target_name)
					f.write("----------------------------------------------------------------------------------------------------------------------------\n")
					f.write("%12s  %12s  %12s  %s\n" % ("milliseconds", "avg time", "#includes", "filename"))
					f.write("----------------------------------------------------------------------------------------------------------------------------\n")
					
					source_files = targets[target_name]
					
					# sorts by value -> source_file_value
					sorted_source_files = sorted(source_files.items(), key=lambda item: item[1][1], reverse=True)
				
					for (k, v) in sorted_source_files:
						(source_file, source_file_value, count, items) = v
						if ignore_single_includes and count == 1:
							continue
						
						real_path = os.path.realpath(source_file)
						if real_path == None or len(real_path) == 0:
							real_path = source_file
						total_milliseconds = int(source_file_value/1000)
						avg_milliseconds = int(total_milliseconds/count)
						
						if sort_by_target and target_name in targets_to_source_files:
							total_items_in_target = len(targets_to_source_files[target_name])
						
						f.write("%12s  %12s  %5s/%-6s  %s\n" % (str(total_milliseconds), str(avg_milliseconds), str(count), str(total_items_in_target), real_path))
						if detailed:
							# split to targets and platforms
							targets_to_platforms_to_items = {}
							for item in items:
								target = item.get_target()
								if target not in targets_to_platforms_to_items:
									targets_to_platforms_to_items[target] = {}
								platforms_to_items = targets_to_platforms_to_items[target]
								platform = item.get_platform()
								if platform not in platforms_to_items:
									platforms_to_items[platform] = []
								platforms_to_items[platform].append(item)
						
							sorted_targets = list(targets_to_platforms_to_items.keys())
							sorted_targets.sort()
						
							if sort_by_target:
								target_header = " "
							else:
								target_header = "[target]"
								
							f.write("   %s %-50s %-10s %-30s %s\n" % (" ", target_header, "[arch]", "[platform]", "[filename]"))
							for target in sorted_targets:
								platforms_to_items = targets_to_platforms_to_items[target]
							
								sorted_platforms = list(platforms_to_items.keys())
								sorted_platforms.sort()
							
								for platform in sorted_platforms:
									items = platforms_to_items[platform]
								
									# we prefix items which have more than one include (only if summarizing globally)
									prefix = " "
									if len(items) > 1 and not sort_by_target:
										prefix = "*"
								
									for item in items:
										target_name = " "
										if not sort_by_target:
											target_name = item.get_target()
										f.write("   %s %-50s %-10s %-30s %s\n" % (prefix, target_name, item.get_arch(), item.get_platform(), item.get_filename()))
							f.write("\n")
			except:
				log.log_warning("Could not write to %s" % most_expensive_includes_path)
				return False
		log.log("Wrote to %s" % most_expensive_includes_path)
		return True
	
	def _write_expensive_includes_sorted_by_file(self, log: Logger, working_path: str, targets: Dict[str, Dict[str, Tuple[str, int, int, List[TimingDataItem]]]]) -> bool:
		'''Writes the expensive includes, sorted by the file.'''
		source_files = {}
		if self._empty_target_name in targets:
			source_files = targets[self._empty_target_name]
		
		# sorts by value -> source_file_value
		sorted_source_files = list(source_files.keys())
		sorted_source_files.sort()
		
		most_expensive_includes_path = os.path.join(working_path, "includes_by_filename.txt")
		log.log_partial_status("Writing summary file sorted by filename...")
		
		# figure out best formatting size
		path_size = 0
		for k in sorted_source_files:
			real_path = os.path.realpath(k)
			if real_path == None or len(real_path) == 0:
				real_path = k
			if len(real_path) > path_size:
				path_size = len(real_path)
		filename_format = "%-{}s".format(str(path_size))
		
		with open(most_expensive_includes_path, 'w') as f:
			try:
				f.write(("{}  %12s  %12s  %12s\n".format(filename_format)) % ("filename", "milliseconds", "avg time", "#includes"))
				f.write("-------------------------------------------------------------\n")
				for k in sorted_source_files:
					v = source_files[k]
					(source_file, source_file_value, count, _) = v
					real_path = os.path.realpath(source_file)
					if real_path == None or len(real_path) == 0:
						real_path = source_file
					total_milliseconds = int(source_file_value/1000)
					avg_milliseconds = int(total_milliseconds/count)
					f.write(("{}  %12s  %12s  %12s\n".format(filename_format)) % (real_path, str(total_milliseconds), str(avg_milliseconds), str(count)))
			except:
				log.log_warning("Could not write to %s" % most_expensive_includes_path)
				return False
		log.log("Wrote to %s" % most_expensive_includes_path)
		return True
	
	def process_comparison(self, comparison: Comparison, last_comparison: Comparison, log: Logger) -> None:
		'''
		No comparison runs as part of this tool.
		'''
		return


if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
