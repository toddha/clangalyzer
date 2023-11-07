import os
import utils.filesizes
from comparison import Comparison, ComparisonOutputType
from logger import Logger
from tool import Tool

class ToolShowBuildFolderSize(Tool):
	def __init__(self):
		self._comparison_key = 'Build Folder Sizes'
		return
	
	def name(self) -> str:
		return 'Show Build Folder Sizes'
	
	def description(self) -> str:
		return 'Generates a summary how big the build folders are on disk.'
	
	def add_arguments(self, parser) -> None:
		parser.add_argument(
			'--no-tool-show-build-folder-size',
			dest='tool_show_build_folder_size',
			action='store_false',
			default=True,
			required=False,
			help='Turns off generating a size summary of the specified build folders.')
		return
	
	def process_arguments(self, args) -> None:
		self._enabled = args.tool_show_build_folder_size
		return
	
	def run(self, context):
		summary_total_key = "*** Total ***"
		summary_total_size = 0
		summary = {}
		
		folders = context.folders()
		path_shortener = context.path_shortener()
		log = context.log()
		for folder in folders:
			log.log_partial_status(f'Scanning {folder}')
			size = 0
			for path, dirs, files in os.walk(folder):
				for filename in files:
					file_path = os.path.join(path, filename)
					if os.path.islink(file_path):
						continue
					file_size = os.path.getsize(file_path)
					log.verbose('file %12s %s' % (utils.filesizes.happy_file_size(file_size), file_path[len(folder):]))
					size += file_size
			log.log('%12s %s' % (utils.filesizes.happy_file_size(size), folder))
			summary_total_size = summary_total_size + size
			summary[path_shortener.shorten_path(folder)] = size
		
		summary[summary_total_key] = summary_total_size
		context.comparison().add_summary(log, self._comparison_key, summary)
		return
	
	def process_comparison(self, comparison: Comparison, last_comparison: Comparison, log: Logger) -> None:
		summary = comparison.summary_data(log=log, name=self._comparison_key)
		last_summary = last_comparison.summary_data(log=log, name=self._comparison_key)
		Comparison.log_summary(key=self._comparison_key, units=ComparisonOutputType.FILESIZE, summary=summary, last_summary=last_summary, log=log)
		return
	

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
