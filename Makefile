# SPEC_ID: venv-always-on (make)
# Generated on 2025-08-31

SHELL := /bin/bash
REPO_ROOT := $(abspath .)
VENV_DIR := $(REPO_ROOT)/.venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

.PHONY: help setup install run-rename run-listup fmt clean

help:
	@echo "Targets:"
	@echo "  setup       - Create venv with python3.11 and install deps"
	@echo "  install     - Install deps into existing venv"
	@echo "  run-rename  - Run receipt_rename.py under venv"
	@echo "  run-listup  - Run listup_receipts.py under venv"
	@echo "  clean       - Remove venv and build artifacts"

setup:
	./scripts/ensure_venv.sh

install:
	$(PIP) install -r requirements.txt

run-rename:
	$(PYTHON) ./receipt_rename.py $(ARGS)

run-listup:
	$(PYTHON) ./listup_receipts.py $(ARGS)

clean:
	rm -rf $(VENV_DIR)

