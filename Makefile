PYTHON ?= python
NPM ?= npm

.PHONY: install test test-backend test-frontend check benchmark benchmark-smoke api web build static-build docker

install:
	$(PYTHON) -m pip install -e "backend[test]"
	$(NPM) --prefix frontend ci

test: test-backend test-frontend

test-backend:
	$(PYTHON) -m pytest backend/tests evaluation/tests

test-frontend:
	$(NPM) --prefix frontend test

check: test
	$(NPM) --prefix frontend run lint
	$(NPM) --prefix frontend run typecheck
	$(NPM) --prefix frontend run build

benchmark:
	$(PYTHON) evaluation/run_benchmark.py

benchmark-smoke:
	$(PYTHON) evaluation/run_benchmark.py --seeds 11,23,37

api:
	cd backend && $(PYTHON) -m causalpilot

web:
	$(NPM) --prefix frontend run dev

build:
	$(NPM) --prefix frontend run build

static-build:
	STATIC_EXPORT=true BASE_PATH=/causalpilot NEXT_PUBLIC_API_BASE_URL=offline $(NPM) --prefix frontend run build

docker:
	docker compose up --build
