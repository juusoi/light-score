PYTHON?=.venv/bin/python

.PHONY: venv sync deps lint fmt ty test ci start

venv:
	uv venv

sync:
	./scripts/uv-sync.sh --all

deps:
	./scripts/install-deps.sh

lint:
	$(PYTHON) -m ruff check .

fmt:
	$(PYTHON) -m ruff format .

ty:
	$(PYTHON) -m ty check . || true

test:
	./scripts/run-tests.sh

ci: lint ty test

start:
	./scripts/run-local.sh
