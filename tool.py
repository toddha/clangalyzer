from comparison import Comparison
from logger import Logger

class Tool:
	def __init__(self):
		# execute all properties to make sure everything is implemented (except for run)
		self.name()
		self.description()
		self.command_line_help()
		self.command_line_default_enabled()
		
		self._enabled = True
		return
	
	def is_enabled(self) -> bool:
		return self._enabled
	
	def name(self) -> str:
		raise AssertionError(f'name must be implemented in unknown class')
		
	def description(self) -> str:
		name = self.name()
		raise AssertionError(f'description must be implemented in {name}')
	
	def add_arguments(self, parser) -> None:
		name = self.name()
		raise AssertionError(f'add_arguments must be implemented in {name}')
	
	def run(self, context):
		name = self.name()
		raise AssertionError(f'run must be implemented in {name}')
	
	def process_arguments(self, args) -> None:
		name = self.name()
		raise AssertionError(f'process_arguments must be implemented in {name}')
	
	def process_comparison(self, comparison: Comparison, last_comparison: Comparison, log: Logger) -> None:
		name = self.name()
		raise AssertionError(f'process_comparison must be implemented in {name}')
		
	

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')