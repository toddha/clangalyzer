import os
import utils.truncation
from comparison import Comparison, ComparisonOutputType
from logger import Logger
from timing_data import TimingData
from tool import Tool

class ToolSerializeProjectTrace(Tool):
	def __init__(self):
		self._comparison_key = 'Serial Times'
		self._comparison_key_total_cpu_time = 'Total CPU seconds'
		self._comparison_key_average_cpu_time = 'Average CPU second per item'
		return
	
	def name(self) -> str:
		return 'Trace Serializer'
	
	def description(self) -> str:
		return 'Generates a single serialized trace for the entire project which combines \
			 	all source files together so that they can be more easily visualized.'
	
	def add_arguments(self, parser) -> None:
		parser.add_argument(
			'--no-tool-serialize',
			dest='tool_serialize',
			action='store_false',
			default=True,
			required=False,
			help='Turns off running the tool which creates a serialized version of the profile data')
		parser.add_argument(
			'--tool-serial-no-serialize',
			dest='tool_serialize_serialize',
			action='store_false',
			default=True,
			required=False,
			help='Turns off actually serializing the json to disk. May still perform analysis.')
		return
	
	def process_arguments(self, args) -> None:
		self._enabled = args.tool_serialize
		self._serialize = args.tool_serialize_serialize
		return
	
	def run(self, context):
		summary = {}
		log = context.log()
		working_path = context.output_path()
		# TODO : do this per project?
		entire_td = TimingData(os.path.join(working_path, "serial_trace.json"), target="", platform="", arch="")
		timing_data_items = context.timing_data_items()
		for item in timing_data_items:
			entire_td.join(item, log)
		if self._serialize:
			if not entire_td.write(context.path_shortener(), log):
				log.log_error_and_exit("Could not serialize trace")
		total_seconds = utils.truncation.truncate_to_place(entire_td.get_total_time() / 1000000, 4)
		timing_data_item_length = len(timing_data_items)
		if timing_data_item_length == 0:
			timing_data_item_length = 1
		average_seconds = utils.truncation.truncate_to_place(total_seconds / timing_data_item_length, 2)
		
		log.log("Took {} CPU seconds".format(total_seconds))
		summary[self._comparison_key_total_cpu_time] = total_seconds
		
		log.log("{} CPU seconds per build item".format(average_seconds))
		summary[self._comparison_key_average_cpu_time] = average_seconds
		
		context.comparison().add_summary(log, self._comparison_key, summary)
		return
	
	def process_comparison(self, comparison: Comparison, last_comparison: Comparison, log: Logger) -> None:
		summary = comparison.summary_data(log=log, name=self._comparison_key)
		last_summary = last_comparison.summary_data(log=log, name=self._comparison_key)
		Comparison.log_summary(key=self._comparison_key, units=ComparisonOutputType.TIME_CPU_SECONDS, summary=summary, last_summary=last_summary, log=log)
		return
	


if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')