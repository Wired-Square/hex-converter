SHELL := /bin/bash
PYTHON := python

APP_NAME := Hex Converter
APP_BUNDLE := dist/$(APP_NAME).app

ICON_SRC_PNG := assets/icon.png
ICONSET_DIR  := build/AppIcon.iconset
ICNS_OUT     := assets/AppIcon.icns

DMG_NAME := $(APP_NAME)-dev.dmg
DMG_PATH := dist/$(DMG_NAME)
STAGING_DIR := build/dmg
DMG_VOLNAME := $(APP_NAME)

SPEC := Hex Converter.spec

.DEFAULT_GOAL := help

.PHONY: help run test install uninstall clean package dmg dmg-clean icons icons-clean

help:
	@echo "Available targets:"
	@echo "  make run        - Run the Hex Converter GUI without installing"
	@echo "  make test       - Run tests with pytest"
	@echo "  make install    - Install in editable mode (pip install -e .)"
	@echo "  make uninstall  - Uninstall the editable package"
	@echo "  make clean      - Remove caches and build artifacts"
	@echo "  make package    - Build a standalone app with PyInstaller"
	@echo "  make dmg        - Create an UNSIGNED development .dmg from dist/*.app"
	@echo "  make icons      - Build assets/AppIcon.icns from assets/icon.png"
	@echo "  make icons-clean- Remove generated iconset and .icns"

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

clean: icons-clean dmg-clean
	@echo "Cleaning up caches..."
	rm -rf .pytest_cache __pycache__ src/hex_converter/__pycache__ tests/__pycache__ build dist *.egg-info

icons:
	@if [ -f "$(ICNS_OUT)" ]; then \
		echo "icons: $(ICNS_OUT) already exists; nothing to do."; \
	elif [ -f "$(ICON_SRC_PNG)" ]; then \
		echo "icons: building .icns from $(ICON_SRC_PNG)..."; \
		command -v sips >/dev/null || { echo "ERROR: 'sips' not found (macOS only)"; exit 1; }; \
		command -v iconutil >/dev/null || { echo "ERROR: 'iconutil' not found (macOS only)"; exit 1; }; \
		rm -rf "$(ICONSET_DIR)"; \
		mkdir -p "$(ICONSET_DIR)"; \
		sips -z 16 16   "$(ICON_SRC_PNG)" --out "$(ICONSET_DIR)/icon_16x16.png" >/dev/null; \
		sips -z 32 32   "$(ICON_SRC_PNG)" --out "$(ICONSET_DIR)/icon_16x16@2x.png" >/dev/null; \
		sips -z 32 32   "$(ICON_SRC_PNG)" --out "$(ICONSET_DIR)/icon_32x32.png" >/dev/null; \
		sips -z 64 64   "$(ICON_SRC_PNG)" --out "$(ICONSET_DIR)/icon_32x32@2x.png" >/dev/null; \
		sips -z 128 128 "$(ICON_SRC_PNG)" --out "$(ICONSET_DIR)/icon_128x128.png" >/dev/null; \
		sips -z 256 256 "$(ICON_SRC_PNG)" --out "$(ICONSET_DIR)/icon_128x128@2x.png" >/dev/null; \
		sips -z 256 256 "$(ICON_SRC_PNG)" --out "$(ICONSET_DIR)/icon_256x256.png" >/dev/null; \
		sips -z 512 512 "$(ICON_SRC_PNG)" --out "$(ICONSET_DIR)/icon_256x256@2x.png" >/dev/null; \
		sips -z 512 512 "$(ICON_SRC_PNG)" --out "$(ICONSET_DIR)/icon_512x512.png" >/dev/null; \
		sips -z 1024 1024 "$(ICON_SRC_PNG)" --out "$(ICONSET_DIR)/icon_512x512@2x.png" >/dev/null; \
		iconutil -c icns -o "$(ICNS_OUT)" "$(ICONSET_DIR)"; \
		echo "icons: created $(ICNS_OUT)"; \
	else \
		echo "icons: no $(ICON_SRC_PNG) or $(ICNS_OUT); skipping (generic icon)."; \
	fi

icons-clean:
	@rm -rf "$(ICONSET_DIR)"

package: icons
	@echo "Building standalone app with PyInstaller..."
	$(PYTHON) -m pip install --upgrade pyinstaller
	@if [ -f "$(SPEC)" ]; then \
		echo "Using spec file: $(SPEC)"; \
		pyinstaller --noconfirm "$(SPEC)"; \
	else \
		echo "Using CLI options (no spec file found)"; \
		pyinstaller --noconfirm \
			--windowed \
			--name "$(APP_NAME)" \
			--icon "$(ICNS_OUT)" \
			--paths src \
			src/hex_converter/__main__.py; \
	fi
	@echo "Build complete! Check the dist/ directory for the app bundle."

dmg: package
	@echo "Creating unsigned development DMG..."
	@rm -rf "$(STAGING_DIR)"
	@mkdir -p "$(STAGING_DIR)"
	@test -d "$(APP_BUNDLE)" || (echo "ERROR: App bundle not found at $(APP_BUNDLE)"; exit 1)
	@cp -R "$(APP_BUNDLE)" "$(STAGING_DIR)/"
	@ln -s /Applications "$(STAGING_DIR)/Applications" || true
	@mkdir -p dist
	hdiutil create -volname "$(DMG_VOLNAME)" -srcfolder "$(STAGING_DIR)" -ov -format UDZO "$(DMG_PATH)"
	@echo "DMG created: $(DMG_PATH)"

dmg-clean:
	@rm -rf "$(STAGING_DIR)" "$(DMG_PATH)"
