#!/bin/sh

# Boot-time security installer for GL-iNet devices
# Sets up the init script to run at boot for MAC and BSSID protection

INIT_SCRIPT="/etc/init.d/gl-mac-security"
CLI_SCRIPT="/usr/bin/blue-code"

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root" >&2
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# Create the security script if blue-code isn't already in PATH
if ! command -v blue-code >/dev/null 2>&1; then
    echo "Creating security script at $CLI_SCRIPT..."
    cat >"$CLI_SCRIPT" <<'EOF'
#!/bin/sh
python3 ##SCRIPT_PATH## "$@"
EOF

    # Replace the path placeholder with actual path
    sed -i "s|##SCRIPT_PATH##|$SCRIPT_DIR/../cli.py" "$CLI_SCRIPT"
    chmod +x "$CLI_SCRIPT"
else
    echo "blue-code command already exists in PATH"
fi

echo "Creating boot-time security init script at $INIT_SCRIPT..."

# Create the boot-time init script
cat >"$INIT_SCRIPT" <<'EOF'
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

# Set permissions
chmod +x "$INIT_SCRIPT"

# Enable the init script to run at boot
echo "Enabling boot-time security script..."
"$INIT_SCRIPT" enable

# Start the service now
echo "Starting boot-time security service..."
"$INIT_SCRIPT" start

echo "Verification:"
echo "-------------"

# Verify init script is installed
if [ -f "$INIT_SCRIPT" ]; then
    echo "✓ Init script installed at $INIT_SCRIPT"
else
    echo "✗ Error: Init script not found"
    exit 1
fi

# Verify script is enabled
if ls /etc/rc.d/S*gl-mac-security >/dev/null 2>&1; then
    echo "✓ Init script is enabled for boot"
else
    echo "✗ Error: Init script not enabled"
    exit 1
fi

# Verify tmpfs is mounted
if mount | grep -q "on /etc/oui-tertf type tmpfs"; then
    echo "✓ tmpfs successfully mounted at /etc/oui-tertf"
else
    echo "✗ Error: tmpfs not mounted correctly"
    exit 1
fi

echo ""
echo "Boot-time security successfully installed and started!"
echo "MAC and BSSID addresses will be randomized on every boot."
echo "Client database is secured in RAM-only storage."
