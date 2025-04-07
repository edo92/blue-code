#!/bin/bash

# GL-iNet Security Tools Installation Script

set -e

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root" >&2
    exit 1
fi

# Base directories
SRC_DIR="$(pwd)/src"
INSTALL_DIR="/usr/local/bin/gl-inet-security"
INIT_SCRIPT="/etc/init.d/gl-mac-security"

# Create directories
echo "Creating installation directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/core"
mkdir -p "$INSTALL_DIR/lib"

# Copy Python files
echo "Copying program files..."
cp -r "$SRC_DIR"/* "$INSTALL_DIR/"

# Create main executable
echo "Creating main executable..."
cat >/usr/bin/gl-security <<'EOF'
#!/bin/sh
python3 /usr/local/bin/gl-inet-security/cli.py "$@"
EOF
chmod +x /usr/bin/gl-security

# Create init script for boot-time MAC security
echo "Creating boot-time security init script..."
cat >"$INIT_SCRIPT" <<'EOF'
#!/bin/sh /etc/rc.common

# Enhanced MAC address and client database security
# Combines RAM-only storage with comprehensive log wiping

# Run before gl-tertf (60) and gl_clients (99)
START=9
STOP=99

start() {
    echo "Starting GL-iNet MAC address security measures..."
    
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
    
    # Run Python-based wiper for additional protection
    gl-security --randomize logs --dry-run
    
    echo "GL-iNet MAC address security measures initialized"
}

stop() {
    echo "Shutting down GL-iNet MAC address security..."
    
    # Secure cleanup on shutdown
    if [ -f /etc/oui-tertf/client.db ]; then
        shred --force --zero --remove /etc/oui-tertf/client.db 2>/dev/null || rm -f /etc/oui-tertf/client.db
    fi
    
    # Unmount tmpfs
    umount -t tmpfs -l /etc/oui-tertf 2>/dev/null
}
EOF

# Set permissions and enable init script
chmod +x "$INIT_SCRIPT"
"$INIT_SCRIPT" enable

echo "Installation complete. Security tools installed to $INSTALL_DIR"
echo "Boot-time security script installed and enabled."
echo ""
echo "Usage:"
echo "  gl-security --randomize all      # Randomize all identifiers"
echo "  gl-security --randomize mac bssid --secure   # Randomize MAC and BSSID with enhanced security"
echo "  gl-security --help               # Show all options"
echo ""
echo "Security services will automatically start on next boot."
echo "To start services now without rebooting:"
echo "  $INIT_SCRIPT start"
