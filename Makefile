
all: test build

test: build
	bin/c_tests
	python3 TestZoa.py

build:
	mkdir -p bin/
	python3 etc/cxt.py README.cxt README.md
	gcc -I. -I../civc/ ../civc/civ/civ* zoa/* -o bin/c_tests
