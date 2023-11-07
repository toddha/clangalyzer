import os
import utils.truncation
from comparison import Comparison
from logger import Logger
from tool import Tool

class ToolFindMostExpensiveFiles(Tool):
	def __init__(self):
		return
	
	def name(self) -> str:
		return 'Most Expensive Source Files'
	
	def description(self) -> str:
		return 'Generates a summary of which were the most expensive files to compile.'
	
	def add_arguments(self, parser) -> None:
		parser.add_argument(
			'--no-tool-show-expensive-source-files',
			dest='tool_show_expensive_source_files',
			action='store_false',
			default=True,
			required=False,
			help='Turns off a summary which outputs the the most expensve source files to compile.')
		return

	def process_arguments(self, args) -> None:
		self._enabled = args.tool_show_expensive_source_files
		return
	
	def run(self, context):
		self._write_summary_to_file(filename = "expensive_files.txt", context = context, summarize_by_target = False)
		self._write_summary_to_file(filename = "expensive_files_by_target.txt", context = context, summarize_by_target = True)
		return
		
	def _write_summary_to_file(self, filename, context, summarize_by_target):
		log = context.log()
		file_path = os.path.join(context.output_path(), filename)
		log.log_partial_status("Writing summary file sorted by time...")
		
		targets_to_timing_items = context.timing_data_items_by_targets()
		
		# dump everything to a single dict
		if not summarize_by_target and len(targets_to_timing_items) > 0:
			empty_target_name = ""
			new_targets_to_timing_items = {}
			new_targets_to_timing_items[empty_target_name] = []
			timing_items = new_targets_to_timing_items[empty_target_name]
			for (_, v) in targets_to_timing_items.items():
				timing_items.extend(v)
			targets_to_timing_items = new_targets_to_timing_items
		
		# sort all items in targets
		for (target_name, v) in targets_to_timing_items.items():
			sorted_items = sorted(v, key=lambda item: item.calculate_total_time(log), reverse=True)
			targets_to_timing_items[target_name] = sorted_items
		
		if len(targets_to_timing_items) == 0:
			log.log_warning('No timing items to analyze')
			return
		
		with open(file_path, 'w') as f:
			for (target_name, items) in targets_to_timing_items.items():
				f.write("\n\n>>>>> %s\n\n" % target_name)
				f.write("----------------------------------------------------------------------------------------------------------------------------\n")
				f.write("%12s  %s\n" % ("seconds", "filename"))
				f.write("----------------------------------------------------------------------------------------------------------------------------\n")
				
				for item in items:
					total_time = item.calculate_total_time(log)
					total_seconds = utils.truncation.truncate_to_place(total_time / 1000000, 4)
					f.write("%12s  %s\n" % (str(total_seconds), item.get_name()))
			
		log.log(f'Wrote to {file_path}')
		return
	
	def process_comparison(self, comparison: Comparison, last_comparison: Comparison, log: Logger) -> None:
		return
		

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
