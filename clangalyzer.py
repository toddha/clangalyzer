#!/usr/bin/env python3 -B

import argparse
import os
import time
from typing import Dict, List, Optional

from context import Context
from logger import Logger
from path_shortener import PathShortener
from timing_data import TimingData

# import tools
from tool import Tool
from tools.tool_find_most_expensive_files import ToolFindMostExpensiveFiles
from tools.tool_find_most_expensive_includes import ToolFindMostExpensiveIncludes
from tools.tool_find_most_expensive_codegen import ToolFindMostExpensiveCodeGen
from tools.tool_gather_trace_files import ToolGatherTraceFiles
from tools.tool_output_target_times import ToolOutputTargetTimes
from tools.tool_serialize_project_trace import ToolSerializeProjectTrace
from tools.tool_show_build_folder_size import ToolShowBuildFolderSize
from tools.tool_show_precomp_header_sizes import ToolShowPrecompHeaderSizes
from tools.tool_clang_breakdown import ToolClangBreakdown


class Clangalyzer:
	'''
	This class effectively is meant to be the main front end for the build timing tools.
	It will gather all build_timing_data it finds based on the input, and run some additional
	tools, such as generating a serialized project trace, and output what it calculates.
	'''
	
	@staticmethod
	def all_tools() -> List[Tool]:
		'''Returns all generic tools that can run on any builds in any projects.'''
		return [
			ToolFindMostExpensiveFiles(),
			ToolFindMostExpensiveIncludes(),
			ToolFindMostExpensiveCodeGen(),
			ToolGatherTraceFiles(),
			ToolOutputTargetTimes(),
			ToolSerializeProjectTrace(),
			ToolShowBuildFolderSize(),
			ToolShowPrecompHeaderSizes(),
			ToolClangBreakdown(),
		]
	
	def __init__(self, tools: List[Tool], context: Context):
		self._context = context
		self._tools = tools
		return
	
	def run(self) -> None:
		'''Run the analysis.'''
		self._context.initialize()
		self._find_build_data()
		self._run_tools()
		
		self._finalize_comparison()
		self._finalize_log()
		
		self._open_output_directory()
		return
	
	def _open_output_directory(self) -> None:
		'''
		Opens the current output directory.
		
		Currently macOS specific.
		'''
		if self._context.should_reveal():
			os.system('/usr/bin/open -R %s' % self._context.output_path())
		return

	def _run_tools(self) -> None:
		'''Runs all tools, skipping those which are disabled.'''
		log = self._context.log()
		for tool in self._tools:
			tool_name = tool.name()
			if not tool.is_enabled():
				log.verbose(f'[Skipping {tool_name} as it is disabled]')
				log.verbose()
				continue
			log.log(f'[Running {tool_name}]')
			tool.run(self._context)
			log.log()
	
	def _find_build_data(self) -> None:
		'''Finds all of the timing build data files.'''
		log = self._context.log()
		log.log("[Finding Build Data]")
		current_stack = self._context.folders()
		if len(current_stack) == 0:
			log.log_warning('No folders were scanned')
		items: List[TimingData] = []
		while len(current_stack) > 0:
			path = current_stack.pop()
			log.log_partial_status("Scanning for files... (%d found)" % len(items), check_last_time=True)
			try:
				listing = os.listdir(path)
			except:
				log.log_warning("Couldn't scan directory " + path)
				continue
			for item in listing:
				item_path = os.path.join(path, item)
				if not os.path.isdir(item_path):
					should_follow_path = False
				elif os.path.islink(item_path):
					should_follow_path = False
				else:
					should_follow_path = True
				if should_follow_path:
					current_stack.append(item_path)
				
				# process item
				data = self._process_item(item_path)
				if data != None:
					assert data is not None
					items.append(data)
		
		self._context.set_timing_data_items(items)
		log.log("Found %d total timing data items" % len(items))
		if len(items) == 0:
			log.log_warning("No timing data items were found")
			log.log("You may be missing the following lines from your build settings")
			log.log("OTHER_CFLAGS = $(inherited) -ftime-trace")
		log.log()
		
		return
	
	def _process_item(self, item_path) -> Optional[TimingData]:
		'''Processes the specific item and returns the TimingData out of it (or None)'''
		log = self._context.log()
		
		# only look at files
		if not os.path.isfile(item_path):
			log.verbose(f'Inspecting {item_path} - not a file')
			return None
		
		# only look at matching file extensions
		extensions = set([".json"])
		ext = os.path.splitext(item_path)[1].lower()
		matches_extension = ext in extensions
		if not ext in extensions:
			log.verbose(f'Inspecting {item_path} - extension is not a known match')
			return None
		
		# to cut down on false positives, only look at paths that contain ".build"
		if item_path.lower().count(".build") == 0:
			log.verbose(f'Inspecting {item_path} - folders is empty and path does not end in \'build\'')
		
		if not self._is_item_non_timing_data_item(item_path):
			return None
		
		if not self._does_item_match_target(item_path):
			return None
		
		# rip target, platform, and arch from the path - which may fail - and if it does, continue
		target_platform_arch = TimingData.target_and_platform_and_arch_from_path(item_path)
		if target_platform_arch == None:
			log.verbose(f'Inspecting {item_path} - does not match known target, platform, or arch')
			return None
		assert target_platform_arch is not None
		(target, platform, arch) = target_platform_arch
		
		# create object and parse
		log.verbose(f'Inspected {item_path} - success')
		td = TimingData(item_path, target, platform, arch)
		if not td.parse(log):
			log.verbose(f'Could not parse')
			return None
		return td
	
	def _is_item_non_timing_data_item(self, item_path: str) -> bool:
		'''cut out well known files that we know aren't valid'''
		item = os.path.basename(item_path)
		log = self._context.log()
		suffixes_to_skip = self._context.get_known_timing_data_item_suffixes_to_skip()
		item_lower = item.lower()
		for suffix_to_skip in suffixes_to_skip:
			if item_lower.endswith(suffix_to_skip):
				log.verbose(f'Inspecting {item_path} - item ends with {suffix_to_skip}')
				return False
		return True
	
	def _does_item_match_target(self, item_path: str) -> bool:
		'''Determines the target of the item and see if it matches our filter (if need be)'''
		if not self._context.has_targets():
			# no targets specified, match all
			return True
		
		targets = self._context.targets()
		log = self._context.log()
		tpa = TimingData.target_and_platform_and_arch_from_path(item_path)
		if tpa == None:
			return False
		
		assert tpa is not None
		(td_target, _, _) = tpa
		td_target = td_target.lower().strip()
		
		target_set = set()
		for target in targets:
			target_set.add(target.lower().strip())
		
		matches = td_target in target_set
		if not matches:
			# ignore platform differences, so atmentionformatter matches atmentionformatter_ios
			target_list: List[str] = list(target_set)
			for target in target_list:
				if td_target.startswith('%s_' % target):
					matches = True
					break
		if not matches:
			log.verbose(f'Inspecting {item_path} - does not match target list')
		return matches
	
	def _finalize_comparison(self) -> None:
		'''Writes the comparison file and outputs any comparison data'''
		log = self._context.log()
		
		# output comparison data
		if self._context.run_comparison():
			log.log("[Outputting Comparison Data]")
			last_comparison = self._context.last_comparison()
			if last_comparison != None:
				comparison = self._context.comparison()
				for tool in self._tools:
					tool.process_comparison(comparison=comparison, last_comparison=last_comparison, log=log)
			log.log()
		
		# write comparison data
		comparison = self._context.comparison()
		output_path = self._context.output_path()
		log.log("[Saving Comparison Data]")
		comparison_path = os.path.join(output_path, self._context.comparison_filename())
		with open(comparison_path, 'w') as f:
			comparison.write_to_file(f)
		log.log(f"Saved to {comparison_path}")
		log.log()
		return
		
	
	def _finalize_log(self) -> None:
		'''Writes the log file'''
		log = self._context.log()
		output_path = self._context.output_path()
		log.log("[Saving Log File]")
		log_path = os.path.join(output_path, 'log.log')
		with open(log_path, 'w') as f:
			log.write_to_file(f)
		return

	@staticmethod
	def add_parser_arguments(parser: argparse.ArgumentParser, tools: List[Tool]):
		'''Adds the default arguments to the parser, including the arguments required by the tool.'''
		parser.add_argument(
			'--output',
			action='store',
			dest='output_path',
			help='The path to save the output to.',
			default=None,
			type=str,
			required=False)
		parser.add_argument(
			'--folder',
			action='append',
			dest='folders',
			help='The folders to inspect for JSON files.',
			type=str,
			default=[])
		parser.add_argument(
			'--verbose',
			dest='verbose',
			action='store_true',
			default=False,
			required=False,
			help='Logs verbosely.')
		parser.add_argument(
			'--no-detailed',
			dest='detailed',
			action='store_false',
			default=True,
			required=False,
			help='Turns off detailed analysis.')
		parser.add_argument(
			'--quiet',
			dest='quiet',
			action='store_true',
			default=False,
			required=False,
			help='Only the comparison data is written to the screen.')
		parser.add_argument(
			'--comparison',
			dest='comparison_path',
			action='store',
			default=None,
			required=False,
			help='The comparison file/folder to use. Ignore the comparison name if specified.')
		parser.add_argument(
			'--no-comparison',
			dest='run_comparison',
			action='store_false',
			default=True,
			required=False,
			help='Disables comparisons. Useful when switching project contexts.')
		parser.add_argument(
			'--comparison-name',
			dest='comparison_name',
			action='store',
			help='The name for the comparison data. When dealing with many different comparison data sets, only sets with the same name will be compared.',
			default=None,
			type=str,
			required=False)
		parser.add_argument(
			'--no-reveal',
			dest='reveal',
			action='store_false',
			default=True,
			required=False,
			help='Disables revealing the output path after finishing the analysis.')
		parser.add_argument(
			'--target',
			dest='targets',
			action='append',
			help='The targets to analyze. If not specified, uses all targets',
			type=str,
			default=[])
		PathShortener.add_parser_arguments(parser)
		for tool in tools:
			tool.add_arguments(parser)
		return

	@staticmethod
	def logger_from_args(args : argparse.Namespace) -> Logger:
		'''Builds the Logger from the argument parser arguments. '''
		return Logger(
			verbose = args.verbose,
			quiet_output = args.quiet,
		)

	@staticmethod
	def context_from_args(log : Logger, args : argparse.Namespace) -> Context:
		'''Builds the Context from the argument parser arguments.'''
		return Context(
			log = log,
			output_path = args.output_path,
			folders = args.folders,
			detailed_analysis = args.detailed,
			reveal = args.reveal,
			run_comparison = args.run_comparison,
			comparison_name = args.comparison_name,
			last_comparison_file_path = args.comparison_path,
			path_shortener = PathShortener.shortener_from_args(log, args),
			targets = set(args.targets)
		)

	@staticmethod
	def tools_process_args(tools : List[Tool], args : argparse.Namespace) -> None:
		'''Process the command line args by all tools.'''
		for tool in tools:
			tool.process_arguments(args)
		return
	

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Parses and analyzes interesting build data to generate helpful data.')
	tools = Clangalyzer.all_tools()
	Clangalyzer.add_parser_arguments(parser, tools)
	
	args = parser.parse_args()
	
	log = Clangalyzer.logger_from_args(args)
	log.log("[[[Running Clangalyzer]]]")
	
	context = Clangalyzer.context_from_args(log, args)
	Clangalyzer.tools_process_args(tools, args)
	analyzer = Clangalyzer(context = context, tools = tools)
	analyzer.run()
	
