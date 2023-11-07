import os
import utils.filesizes
from comparison import Comparison, ComparisonOutputType
from logger import Logger
from tool import Tool

class ToolShowPrecompHeaderSizes(Tool):
	def __init__(self):
		self._comparison_key = 'Precompiled Header Sizes'
		return
	
	def name(self) -> str:
		return 'Show Precomp Header Sizes'
	
	def description(self) -> str:
		return 'Generates a summary how big the precompiled header object files are on disk.'
	
	def add_arguments(self, parser) -> None:
		parser.add_argument(
			'--no-tool-show-precomp-header-sizes',
			dest='tool_show_precomp_header_sizes',
			action='store_false',
			default=True,
			required=False,
			help='Turns off running which outputs the size of the precompiled header object files.')
		return
	
	def process_arguments(self, args) -> None:
		self._enabled = args.tool_show_precomp_header_sizes
		return
	
	def run(self, context):
		summary_total_key = "*** Total ***"
		summary_total_size = 0
		summary = {}
		
		valid_extensions = set(['.gch'])
		log = context.log()
		path_shortener = context.path_shortener()
		folders = context.folders()
		files_found = {}
		for folder in folders:
			log.log_partial_status(f'Scanning {folder}')
			size = 0
			for path, dirs, files in os.walk(folder):
				for filename in files:
					ext = os.path.splitext(filename)[1].lower()
					matches_extension = ext in valid_extensions
					file_path = os.path.join(path, filename)
					if not matches_extension:
						log.verbose(f'{file_path} does not match extensions')
						continue
					
					file_size = os.path.getsize(file_path)
					log.verbose('file %12s %s' % (utils.filesizes.happy_file_size(file_size), file_path[len(folder):]))
					size += file_size
					files_found[file_path] = file_size
					summary[path_shortener.shorten_path(file_path)] = file_size
					summary_total_size = summary_total_size + file_size
			log.log('%12s %s' % (utils.filesizes.happy_file_size(size), folder))
			summary[path_shortener.shorten_path(folder)] = size
		summary[summary_total_key] = summary_total_size
		context.comparison().add_summary(log, self._comparison_key, summary)
		
		if len(files_found) == 0:
			log.log("NOTE: No precompiled headers found")
			log.log("If this is unexpected, ensure you have the following build settings")
			log.log("GCC_PRECOMPILE_PREFIX_HEADER = YES")
			log.log("GCC_PREFIX_HEADER = <something>")
		
		return
	
	def process_comparison(self, comparison: Comparison, last_comparison: Comparison, log: Logger) -> None:
		summary = comparison.summary_data(log=log, name=self._comparison_key)
		last_summary = last_comparison.summary_data(log=log, name=self._comparison_key)
		Comparison.log_summary(key=self._comparison_key, units=ComparisonOutputType.FILESIZE, summary=summary, last_summary=last_summary, log=log)
		return

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
