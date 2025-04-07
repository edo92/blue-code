# Makefile for GL-iNet Security Tools

.PHONY: install uninstall clean dev

# Default target
all: install

# Install the tools
install:
	@echo "Installing GL-iNet Security Tools..."
	@if [ $$(id -u) -ne 0 ]; then \
		echo "Error: Installation requires root privileges"; \
		echo "Please run: sudo make install"; \
		exit 1; \
	fi
	@chmod +x install.sh
	@./install.sh

# Development installation (for testing without system-wide impact)
dev:
	@echo "Installing for development..."
	pip3 install -e .

# Uninstall the tools
uninstall:
	@echo "Uninstalling GL-iNet Security Tools..."
	@if [ $$(id -u) -ne 0 ]; then \
		echo "Error: Uninstallation requires root privileges"; \
		echo "Please run: sudo make uninstall"; \
		exit 1; \
	fi
	pip3 uninstall -y gl-inet-v2
	rm -f /usr/bin/gl-secure
	rm -f /usr/bin/gl-mac
	rm -f /usr/bin/gl-bssid
	@echo "Uninstallation complete"

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	rm -rf __pycache__
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete