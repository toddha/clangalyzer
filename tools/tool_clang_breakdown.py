import os
import shutil
import utils.truncation
from comparison import Comparison, ComparisonOutputType
from logger import Logger
from tool import Tool

class ToolClangBreakdown(Tool):
	def __init__(self):
		self._comparison_key = 'Clang Breakdown'
		return
	
	def name(self) -> str:
		return 'Clang Breakdown'
	
	def description(self) -> str:
		return 'Shows a breakdown of the steps clang is spending time on'
	
	def add_arguments(self, parser) -> None:
		parser.add_argument(
			'--no-tool-clang-breakdown',
			dest='tool_clang_breakdown',
			action='store_false',
			default=True,
			required=False,
			help='Turns off a summary shows a breakdown of what clang is spending time on.')
		return
	
	def process_arguments(self, args) -> None:
		self._enabled = args.tool_clang_breakdown
		return
	
	def run(self, context):
		summary = {}
		summary_total_key = "*** Total ***"
		summary_total_time = 0

		# Future improvements: break these down by target as today we just treat the entire project
		# as one big library.

		log = context.log()
		
		timing_datas = context.timing_data_items()
		items_by_name = {}
		for timing_data in timing_datas:
			timing_data_items = timing_data.get_items()
			for timing_data_item in timing_data_items:
				name = timing_data_item.get_short_total_name()
				if len(name) == 0:
					continue
				if name not in items_by_name:
					items_by_name[name] = [timing_data_item]
				else:
					items_by_name[name].append(timing_data_item)
		
		names = list(items_by_name.keys())
		names.sort()
		for name in names:
			total_duration = 0
			items = items_by_name[name]
			for item in items:
				total_duration += item.get_duration()
			summary_total_time += total_duration
			total_duration_seconds = utils.truncation.truncate_to_place(float(total_duration) / float(1000000), 2)
			seconds_string = f'{total_duration_seconds}'
			if seconds_string == "0.0":
				continue
			total_duration_ms = int(total_duration / 1000)
			summary[name] = total_duration_ms
			log.log('%40s %s seconds' % (name, seconds_string))
		
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
