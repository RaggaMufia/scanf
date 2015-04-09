.PHONY: test package

test:
	python2 scanf.py
	python3 scanf.py

package:
	exit 1
