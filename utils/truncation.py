def truncate_to_place(value: float, num: int) -> float:
	'''
	Truncates the given value to a specified decimal place.
	
	Only 2 and 4 are well supported in terms of decimal places.
	'''
	for i in range(num):
		value = value * float(10)
	value = float(int(value))
	if num == 2:
		value = value / 100
	elif num == 4:
		value = value / 10000
	else:
		for i in range(num):
			value = value / 10
	return value
	

if __name__ == "__main__":
	raise AssertionError('Error: Please do not run this script directly.')
