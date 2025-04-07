#!/bin/sh

# Exit on errors
set -e

echo "Starting BlueCode Security Tools installation..."

# # Install Python dependencies
# if command -v opkg >/dev/null 2>&1; then
#     # OpenWrt/GL-iNet environment
#     echo "Detected OpenWrt/GL-iNet environment"
#     opkg update
#     opkg install python3
#     opkg install python3-pip
# else
#     # Regular Linux environment
#     echo "Regular Linux environment detected"
#     # Check if pip3 is installed
#     if ! command -v pip3 >/dev/null 2>&1; then
#         echo "Error: pip3 not found. Please install Python 3 and pip."
#         exit 1
#     fi
# fi

# Install Python package with entry points
echo "Installing Python package..."
pip3 install -e .

# Create the necessary directories
mkdir -p /etc/hotplug.d/button
mkdir -p /usr/lib/blue-code

# Install button script for toggling display
echo "Setting up button script..."
cp ./src/usr/50-toggle_display /etc/hotplug.d/button/
chmod +x /etc/hotplug.d/button/50-toggle_display

# Install boot-time security script WITHOUT running it
echo "Setting up boot-time security script (without running it)..."
cp ./src/etc/boot-security.sh /usr/lib/blue-code/boot-security.sh
chmod +x /usr/lib/blue-code/boot-security.sh

# Create init.d script without enabling it
cat >/etc/init.d/gl-mac-security <<'EOF'
#!/bin/sh /etc/rc.common

# Enhanced MAC address and client database security
# Combines RAM-only storage with comprehensive security

# Run before gl-tertf (60) and gl_clients (99)
START=9
STOP=99

start() {
    echo "Starting BlueCode security measures..."
    
    # Create tmpfs mount for client database
    tmpdir="$(mktemp -d)"
    # Mount tmpfs to temporary directory
    mount -t tmpfs tmpfs "$tmpdir"
    
    # Backup client database if it exists
    if [ -f /etc/oui-tertf/client.db ]; then
        cp -a /etc/oui-tertf/client.db "$tmpdir/"
        # Securely shred the original database
        shred --force --zero --remove /etc/oui-tertf/client.db 2>/dev/null || rm -f /etc/oui-tertf/client.db
    fi
    
    # Unmount any existing tmpfs at client database location
    umount -t tmpfs -l /etc/oui-tertf 2>/dev/null
    
    # Create directory if it doesn't exist
    mkdir -p /etc/oui-tertf
    
    # Mount tmpfs at client database location
    mount -t tmpfs tmpfs /etc/oui-tertf
    
    # Restore database structure if backup exists
    if [ -f "$tmpdir/client.db" ]; then
        cp -a "$tmpdir/client.db" /etc/oui-tertf/
    fi
    
    # Clean up temporary directory
    umount -t tmpfs -l "$tmpdir" 2>/dev/null
    rmdir "$tmpdir"
    
    # Run MAC and BSSID randomization
    blue-code
    
    echo "BlueCode security measures initialized"
}

stop() {
    echo "Shutting down BlueCode security..."
    
    # Secure cleanup on shutdown
    if [ -f /etc/oui-tertf/client.db ]; then
        shred --force --zero --remove /etc/oui-tertf/client.db 2>/dev/null || rm -f /etc/oui-tertf/client.db
    fi
    
    # Unmount tmpfs
    umount -t tmpfs -l /etc/oui-tertf 2>/dev/null
}
EOF

chmod +x /etc/init.d/gl-mac-security

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
echo "To enable boot-time randomization, run: /etc/init.d/gl-mac-security enable"
echo "To start randomization now, run: /etc/init.d/gl-mac-security start"
echo "For backward compatibility, use 'blue-code secure --dry-run --verbose'"
