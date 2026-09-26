.PHONY: venv test

venv: .venv/.installed

.venv/.installed: requirements.txt requirements-dev.txt
	python3 -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))'
	python3 -m venv .venv && .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements-dev.txt && touch .venv/.installed

test: venv
	.venv/bin/python -m pytest -q -m "not docker and not smoke"
