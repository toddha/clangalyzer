import os
from context import Context
from comparison import Comparison, ComparisonOutputType
from logger import Logger
from tool import Tool
from timing_data_item import TimingDataItem
from typing import Dict, List, Set, Tuple

class ToolFindMostExpensiveCodeGen(Tool):
	def __init__(self):
		self._summary_key_total_time = "*** Total ***"
		self._comparison_key = 'CodeGen Times'
		return
	
	def name(self) -> str:
		return 'Expensive CodeGen'
	
	def description(self) -> str:
		return 'Outputs the summaries of which functions take the longest to generate code.'
	
	def add_arguments(self, parser) -> None:
		parser.add_argument(
			'--no-tool-find-expensive-codegen',
			dest='tool_find_expensive_codegen',
			action='store_false',
			default=True,
			required=False,
			help='Turns off running the tool which finds the most expensive functions to codegen.')
		return
	
	def process_arguments(self, args) -> None:
		self._enabled = args.tool_find_expensive_codegen
		return
	
	def run(self, context: Context):
		log = context.log()

		codegen_function_items: List[TimingDataItem] = []
		codegen_function_items_by_target: Dict[str, List[TimingDataItem]] = {}

		total_duration_ns = 0
		timing_items = context.timing_data_items()
		for timing_item in timing_items:
			log.log_partial_status("Inspecting %s"  % timing_item.get_name())
			
			items = timing_item.get_items()
			for item in items:
				if not item.is_codegen_function():
					continue
				
				# avoid outputting anything under 0ms
				duration_ns = item.get_duration()
				total_duration_ns += duration_ns
				duration_ms = int(duration_ns / 1000)
				if duration_ms == 0:
					continue

				function_name = item.get_detail()
				if len(function_name) == 0:
					log.log_warning("no function name associated with codegen item")
					continue

				codegen_function_items.append(item)

				target = item.get_target()
				if target not in codegen_function_items_by_target:
					codegen_function_items_by_target[target] = [item]
				else:
					codegen_function_items_by_target[target].append(item)

		log.log("Found %d codegen items (%dms)" % (len(codegen_function_items), total_duration_ns / 1000))
		
		# sort
		codegen_function_items.sort(key=lambda x: x.get_duration(), reverse=True)
		for (k, v) in codegen_function_items_by_target.items():
			v.sort(key=lambda x: x.get_duration(), reverse=True)

		# output
		# show the top 20 items
		summary_items = codegen_function_items[:20]
		format_string = "   %10s  %35s   %s"
		print(format_string % ("Time", "Target", "Function"))
		for summary_item in summary_items:
			duration_in_ms = "%dms" % (int(summary_item.get_duration() / 1000))
			print(format_string % (duration_in_ms, summary_item.get_target(), summary_item.get_detail()))
		
		if not self._write_summary_for_targets(context, codegen_function_items_by_target):
			return False

		summary = {}
		summary[self._summary_key_total_time] = total_duration_ns / 1000
		context.comparison().add_summary(log, self._comparison_key, summary)
		return True
	
	def _write_summary_for_targets(self, context: Context, codegen_function_items_by_target: Dict[str, List[TimingDataItem]]) -> bool:
		log = context.log()
		
		file_name = "expensive_codegen_by_target.txt"
		
		most_expensive_codegen_path = os.path.join(context.output_path(), file_name)
		log.log_partial_status("Writing target summary file...")
		
		try:
			with open(most_expensive_codegen_path, 'w') as f:
				total_items_in_target = 0
				target_names = list(codegen_function_items_by_target.keys())
				target_names.sort()
				format_string = "%12s   %s\n"
				for target_name in target_names:
					f.write("\n\n>>>>> %s\n\n" % target_name)
					f.write("----------------------------------------------------------------------------------------------------------------------------\n")
					f.write(format_string % ("milliseconds", "function"))
					f.write("----------------------------------------------------------------------------------------------------------------------------\n")
					codegen_function_items = codegen_function_items_by_target[target_name]
					for item in codegen_function_items:
						duration_in_ms = "%d" % (int(item.get_duration() / 1000))
						f.write(format_string % (duration_in_ms, item.get_detail()))
					f.write("\n")
		except:
			log.log_warning("Could not write to %s" % most_expensive_codegen_path)
			return False

		return True

	def process_comparison(self, comparison: Comparison, last_comparison: Comparison, log: Logger) -> None:
		summary = comparison.summary_data(log=log, name=self._comparison_key)
		last_summary = last_comparison.summary_data(log=log, name=self._comparison_key)
		Comparison.log_summary(key=self._comparison_key, units=ComparisonOutputType.TIME_MILLISECONDS, summary=summary, last_summary=last_summary, log=log)
		return

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
