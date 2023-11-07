def happy_file_size(size) -> str:
	'''
	Returns the happy file size of the number (i.e. 384039 -> 375KB).
	
	Currently based on 1024, not 1000.
	'''
	size = float(size)
	items = " bytes"
	noFloat = False
	if (size > 1024*1024*1024):
		size = size / float(1024 * 1024 * 1024)
		items = "GB"
	elif (size > 1024*1024):
		size = size / float(1024 * 1024)
		items = "MB"
	elif (size > 1024):
		size = size / float(1024)
		items = "KB"
	else:
		noFloat = True
	if (noFloat):
		size = int(size)
	else:
		size = float(int(size * 100)) / 100
	return str(size) + items

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
