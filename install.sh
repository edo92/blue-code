#!/bin/sh

# Exit on errors
set -e

echo "Starting BlueCode Security Tools installation..."

# Install Python dependencies
if command -v opkg >/dev/null 2>&1; then
    # OpenWrt/GL-iNet environment
    echo "Detected OpenWrt/GL-iNet environment"
    opkg update
    opkg install python3
    opkg install python3-pip
else
    # Regular Linux environment
    echo "Regular Linux environment detected"
    # Check if pip3 is installed
    if ! command -v pip3 >/dev/null 2>&1; then
        echo "Error: pip3 not found. Please install Python 3 and pip."
        exit 1
    fi
fi

# Install Python package with entry points
echo "Installing Python package..."
pip3 install -e .

# Create the necessary directories
mkdir -p /etc/hotplug.d/button

# Install button script for toggling display
echo "Setting up button script..."
cp ./src/usr/50-toggle_display /etc/hotplug.d/button/
chmod +x /etc/hotplug.d/button/50-toggle_display

# Check if we're on a GL-iNet device with e750_mcu
if [ -f /etc/init.d/e750_mcu ]; then
    echo "Restarting e750_mcu service..."
    /etc/init.d/e750_mcu restart
fi

# Install boot-time security script
echo "Setting up boot-time security..."
chmod +x src/etc/boot-security.sh
sh src/etc/boot-security.sh

# Verify the installation
echo "\nVerifying installation:"
if command -v blue-code >/dev/null 2>&1; then
    echo "✓ blue-code command is available"
else
    echo "✗ blue-code command not found. Installation may have failed."
    echo "  Try running 'make symlinks' to create manual symlinks."
fi

echo "\nInstallation completed successfully!"
echo "Use 'blue-code' to run all randomizations."
echo "For help, use 'blue-code --help'"
echo "For backward compatibility, use 'blue-code secure --dry-run --verbose'"
