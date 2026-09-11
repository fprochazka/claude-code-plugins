# Repository checks for this marketplace. `make` runs everything; run `make all` before you push.

.PHONY: all check validate test hooks

all: check validate test

check:
	scripts/check.sh

# The plugin validator is the only thing that reads the manifests the way Claude Code does.
# Plugins without a manifest (queued for deletion) are skipped.
validate:
	claude plugin validate --strict .
	@for dir in plugins/*/; do \
		if [ -f "$$dir.claude-plugin/plugin.json" ]; then \
			echo "==> $$dir"; \
			claude plugin validate --strict "$$dir" || exit 1; \
		fi; \
	done

test:
	python3 -m unittest discover -s plugins/noisy-tools-in-subagent/hooks -p 'test_*.py'
	bash plugins/rabbitmqadmin/scripts/test-validate-readonly.sh

# One-off per clone. The patterns file the hooks read is deliberately not in the repo, so its path
# has to be set by hand.
hooks:
	git config core.hooksPath scripts/hooks
	@echo "hooks installed. Now point them at your patterns file, one extended regex per line:"
	@echo "  git config hooks.forbiddenPatternsFile <path to a file outside this repo>"
