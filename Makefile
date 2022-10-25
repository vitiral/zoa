
all: test build

test:
	python3 TestZoa.py

build:
	python3 etc/cxt.py README.cxt README.md
