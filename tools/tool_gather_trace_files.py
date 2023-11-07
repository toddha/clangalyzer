import os
import shutil
from comparison import Comparison
from logger import Logger
from tool import Tool

class ToolGatherTraceFiles(Tool):
	def __init__(self):
		return
	
	def name(self) -> str:
		return 'Trace File Gatherer'
	
	def description(self) -> str:
		return 'Gathers all of the trace files for a snapshot'
	
	def add_arguments(self, parser) -> None:
		parser.add_argument(
			'--tool-gather',
			dest='tool_gather',
			action='store_true',
			default=False,
			required=False,
			help='Turns on gathering trace files')
		return
	
	def process_arguments(self, args) -> None:
		self._enabled = args.tool_gather
		return
	
	def run(self, context):
		log = context.log()
		gather_path = os.path.join(context.output_path(), "traces")
		if not os.path.exists(gather_path):
			log.verbose('Creating traces path...')
			os.mkdir(gather_path)
			log.verbose(f'Created traces path at {gather_path}')
		
		count = 0
		timing_data = context.timing_data_items()
		for td in timing_data:
			item_path = td.get_path()
			dest_name = os.path.basename(item_path)
			log.log_partial_status(f'Collecting dest_name')
			count = count + 1
			
			suffix_count = 1
			
			while True:
				# most of the time, we end up with a version for mac and a version for iOS
				# so we expect duplicates. We can also get duplicates if we have two files
				# named the same thing over a variety of projects (consider util.cpp)
				if suffix_count > 1:
					(dest_filename, dest_ext) = os.path.splitext(dest_name)
					dest_name = '{}-{}{}'.format(dest_filename, suffix_count, dest_ext)
				dest_path = os.path.join(gather_path, dest_name)
				if not os.path.exists(dest_path):
					break
				suffix_count = suffix_count + 1
			log.verbose('Copying {} -> {}'.format(item_path, dest_path))
			try:
				# would be good to clone, but waiting for the new clone python liblet to handle this for us.
				shutil.copy2(item_path, dest_path)
			except:
				log.log_warning('Failed to gather {})'.format(item_path))
		log.log(f'Collected {count} files')
		return
	
	def process_comparison(self, comparison: Comparison, last_comparison: Comparison, log: Logger) -> None:
		return

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')