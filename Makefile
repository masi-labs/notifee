.PHONY: test-unit lint lint-src lint-tests

test-unit:
	python -m pytest tests/unit

lint: lint-src lint-tests

lint-src:
	pylint --rcfile=.pylintrc src/notifee

lint-tests:
	pylint --rcfile=.pylintrc-tests tests/
