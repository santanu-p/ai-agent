SHELL := /bin/sh

.PHONY: help test test-python test-ts run-control run-runtime run-learning run-security

help:
	@echo "Targets:"
	@echo "  test           - run TypeScript and Python tests"
	@echo "  test-python    - run Python tests in service folders"
	@echo "  test-ts        - run control-plane tests"
	@echo "  compose-up     - start local stack via docker compose"

test: test-ts test-python

test-ts:
	cd apps/control-plane && npm install && npm run test

test-python:
	cd services/runtime-plane && pip install -r requirements.txt && pytest
	cd services/learning-plane && pip install -r requirements.txt && pytest
	cd services/security-plane && pip install -r requirements.txt && pytest

compose-up:
	docker compose up --build

