
all: test build

test: testPy testC

testPy:
	python3 TestZoa.py

testC:
	gcc -m32 civ/*.c -o bin/a.out
	./bin/a.out

build:
	python3 etc/cxt.py README.cxt README.md
