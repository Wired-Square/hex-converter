# Use bash for consistent behavior
SHELL := /bin/bash

# Python interpreter (change if using pyenv/conda)
PYTHON := python

# Default target
.DEFAULT_GOAL := help

help:
	@echo "Available targets:"
	@echo "  make run       - Run the Hex Converter GUI without installing"
	@echo "  make test      - Run tests with pytest"
	@echo "  make install   - Install in editable mode (pip install -e .)"
	@echo "  make uninstall - Uninstall the editable package"
	@echo "  make clean     - Remove caches and build artifacts"

run:
	@echo "Running Hex Converter GUI..."
	PYTHONPATH=src $(PYTHON) -m hex_converter

test:
	@echo "Running tests..."
	PYTHONPATH=src pytest -q

install:
	@echo "Installing Hex Converter in editable mode..."
	$(PYTHON) -m pip install -e .

uninstall:
	@echo "Uninstalling Hex Converter..."
	$(PYTHON) -m pip uninstall -y hex-converter

clean:
	@echo "Cleaning up caches..."
	rm -rf .pytest_cache __pycache__ src/hex_converter/__pycache__ tests/__pycache__ build dist *.egg-info

