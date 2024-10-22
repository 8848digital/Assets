import sys

MAX_LINES = 10000


def main(argv):
	files = argv[1:]
	for file_path in files:
		with open(file_path) as file:
			lines = file.readlines()
			if len(lines) > MAX_LINES:
				print(f"Error: File {file_path} has more than {MAX_LINES} lines.")
				sys.exit(1)


if __name__ == "__main__":
	main(sys.argv)