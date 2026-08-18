.PHONY: test codex-hooks

test:
	@for f in tests/test_*.py; do \
		echo "== $$f"; \
		python3 "$$f" || exit 1; \
	done

# Render codex/hooks.json with this checkout's path and install it.
# Refuses to clobber an existing ~/.codex/hooks.json — merge by hand instead.
codex-hooks:
	@if [ -e "$$HOME/.codex/hooks.json" ]; then \
		echo "~/.codex/hooks.json exists — merge codex/hooks.json into it by hand"; exit 1; \
	fi
	@mkdir -p "$$HOME/.codex"
	@sed "s|SCRIM_ROOT|$(CURDIR)|g" codex/hooks.json > "$$HOME/.codex/hooks.json"
	@echo "installed ~/.codex/hooks.json — run /hooks inside codex to trust it"
