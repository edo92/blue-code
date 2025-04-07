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

    # Run MAC and BSSID randomization WITHOUT IMEI changes at boot
    # Use a specific set of randomizations that won't trigger a reboot
    bluecode --randomize mac bssid logs --no-restart

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
