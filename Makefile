.PHONY: test

test:
	python3 tests/test_shrink.py
	python3 tests/test_compress.py
	python3 tests/test_reducer.py
	python3 tests/test_constrain.py
	python3 tests/test_stash.py
	python3 tests/test_observe.py
