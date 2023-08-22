VENV ?= .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff

.PHONY: help venv install migrate run test coverage lint format check

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-10s %s\n", $$1, $$2}'

venv: ## Create the virtualenv
	python3 -m venv $(VENV)

install: venv ## Install runtime and development dependencies
	$(PIP) install -r requirements-dev.txt

migrate: ## Apply database migrations
	$(PY) manage.py migrate

run: ## Start the development server on :8000
	$(PY) manage.py runserver

test: ## Run the test suite
	DJANGO_DEBUG=1 $(PY) manage.py test

coverage: ## Run the suite under coverage and print the report
	DJANGO_DEBUG=1 $(PY) -m coverage run manage.py test
	$(PY) -m coverage report

lint: ## Lint and check formatting
	$(RUFF) check .
	$(RUFF) format --check .

format: ## Apply formatting and safe lint fixes
	$(RUFF) check --fix .
	$(RUFF) format .

check: lint test ## Everything CI would run
