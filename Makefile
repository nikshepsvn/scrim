.PHONY: test

test:
	@for f in tests/test_*.py; do \
		echo "== $$f"; \
		python3 "$$f" || exit 1; \
	done
