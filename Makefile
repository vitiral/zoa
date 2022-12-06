
all: test build

test: build
	bin/c_tests
	python3 TestZoa.py
	./zoa_export.py data/small.ty bin/small
	cat bin/small.h

build:
	mkdir -p bin/
	python3 etc/cxt.py README.cxt README.md
	gcc -I. -I../civc/ ../civc/civ/civ* zoa/* -o bin/c_tests
