#* Variables
SHELL := /usr/bin/env bash
PYTHON := python3.11

#* Directories with source code
CODE = base
TESTS = tests

#* Poetry
.PHONY: poetry-download
poetry-download:
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | $(PYTHON) -

#* Installation
.PHONY: install
install:
	poetry install -n
	poetry run mypy --install-types --non-interactive $(CODE)

.PHONY: pre-commit-install
pre-commit-install:
	pre-commit install

#* Formatters
.PHONY: codestyle
codestyle:
	pyupgrade --exit-zero-even-if-changed --py39-plus **/*.py
	autoflake --recursive --in-place --remove-all-unused-imports --ignore-init-module-imports $(CODE)
	isort --settings-path pyproject.toml $(CODE)
	black --config pyproject.toml $(CODE)
