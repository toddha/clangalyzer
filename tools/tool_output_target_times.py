import os
import utils.truncation
from comparison import Comparison, ComparisonOutputType
from logger import Logger
from tool import Tool

class ToolOutputTargetTimes(Tool):
	def __init__(self):
		self._comparison_key = 'Target Times'
		return
	
	def name(self) -> str:
		return 'Determine Target Times'
	
	def description(self) -> str:
		return 'Generates a summary which breaks down how long each target in the compilation process takes.'
	
	def add_arguments(self, parser) -> None:
		parser.add_argument(
			'--no-tool-output-target-times',
			dest='tool_output_target_times',
			action='store_false',
			default=True,
			required=False,
			help='Turns off running the tool which outputs the times for each target.')
		return
	
	def process_arguments(self, args) -> None:
		self._enabled = args.tool_output_target_times
		return
	
	def run(self, context):
		summary = {}
		summary_total_key = "*** Total ***"
		summary_total_time = 0
		
		target_times = {}
		output_path = context.output_path()
		timing_items = context.timing_data_items()
		for td in timing_items:
			target = td.get_target()
			existing_time = 0
			if target in target_times:
				existing_time = target_times[target]
			for item in td.get_items():
				# we only care about total execute compiler
				if not item.is_total_execute_compiler():
					continue
				item_time = item.get_duration()
				summary_total_time = summary_total_time + item_time
				existing_time = existing_time + item_time
			target_times[target] = existing_time
		log = context.log()
		
		targets = list(target_times.keys())
		targets.sort()
		if len(targets) == 0:
			log.log_warning("No targets to determine times for")
			return
		
		project_timing_path = os.path.join(output_path, "target_timing.txt")
		with open(project_timing_path, 'w') as f:
			f.write("Total target times (in CPU seconds)\n")
			for target in targets:
				total_time = target_times[target]
				total_seconds = utils.truncation.truncate_to_place(total_time / 1000000, 2)
				f.write("%-50s : " % target)
				f.write("{}\n".format(total_seconds))
				total_milliseconds = int(total_time / 1000)
				summary[target] = total_milliseconds
			if len(targets) == 0:
				log.log_warning("No targets were found")
			else:
				log.log('Found %d targets' % len(targets))
		summary[summary_total_key] = int(summary_total_time / 1000)
		
		context.comparison().add_summary(log, self._comparison_key, summary)
		return
	
	def process_comparison(self, comparison: Comparison, last_comparison: Comparison, log: Logger) -> None:
		summary = comparison.summary_data(log=log, name=self._comparison_key)
		last_summary = last_comparison.summary_data(log=log, name=self._comparison_key)
		Comparison.log_summary(key=self._comparison_key, units=ComparisonOutputType.TIME_MILLISECONDS, summary=summary, last_summary=last_summary, log=log)
		return

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
