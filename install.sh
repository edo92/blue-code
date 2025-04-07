#!/bin/sh
set -eu

# Ensure the script is run as root.
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root." >&2
    exit 1
fi

# Display usage instructions.
usage() {
    echo "Usage: $0 [--no-switch]"
    echo "Options:"
    echo "  --no-switch  Skip installation of button switch script"
    exit 1
}

# Parse command-line arguments.
DISABLE_SWITCH=0
if [ "$#" -gt 1 ]; then
    usage
elif [ "$#" -eq 1 ]; then
    if [ "$1" = "--no-switch" ]; then
        DISABLE_SWITCH=1
    else
        usage
    fi
fi

# Logging helpers.
log() {
    echo "[INFO] $*"
}

error() {
    echo "[ERROR] $*" >&2
}

# Create necessary directories
create_directories() {
    log "Creating essential directories..."
    mkdir -p /etc/bluecode/templates
    mkdir -p /usr/lib/bluecode
    mkdir -p /etc/hotplug.d/button
}

# Install Python dependencies based on the environment.
install_python_dependencies() {
    if command -v opkg >/dev/null 2>&1; then
        log "Detected OpenWrt/GL-iNet environment"
        opkg update
        opkg install python3 python3-pip
    else
        log "Regular Linux environment detected"
        if ! command -v pip3 >/dev/null 2>&1; then
            error "pip3 not found. Please install Python 3 and pip."
            exit 1
        fi
    fi
}

# Install the Python package.
install_python_package() {
    log "Installing Python package..."
    pip3 install .
}

# Optionally set up the switch button script.
setup_switch_button_script() {
    if [ "$DISABLE_SWITCH" -eq 0 ]; then
        log "Setting up button script..."
        # Ensure destination directory exists.
        [ -d /etc/hotplug.d/button ] || mkdir -p /etc/hotplug.d/button
        cp ./config/hotplug/50-toggle_wireless /etc/hotplug.d/button/
        chmod +x /etc/hotplug.d/button/50-toggle_wireless
    else
        log "Switch button script installation skipped as per argument."
    fi
}

# Set up the boot script.
setup_boot_script() {
    log "Setting up boot script..."
    cp ./config/init.d/boot.template /etc/init.d/gl-mac-security
    chmod +x /etc/init.d/gl-mac-security

    log "Boot script installed but not enabled."
    log "To enable at startup, run: /etc/init.d/gl-mac-security enable"
    log "To start now, run: /etc/init.d/gl-mac-security start"
}

# Set up the CLI command and backup any existing binary.
setup_cli_command() {
    log "Setting up executable links..."
    if [ -f /usr/bin/bluecode ]; then
        log "Backing up existing bluecode command..."
        mv /usr/bin/bluecode /usr/bin/bluecode.backup
    fi

    log "Installing CLI command script..."
    cp ./scripts/bluecode /usr/bin/bluecode
    chmod +x /usr/bin/bluecode
}

# Verify the installation by checking the commands.
verify_installation() {
    log "Verifying installation..."

    if command -v bluecode >/dev/null 2>&1; then
        log "✓ bluecode command is available"
    else
        error "✗ bluecode command not found. Installation may have failed."
        exit 1
    fi

    if [ -f /etc/init.d/gl-mac-security ]; then
        log "✓ Boot-time security script is installed"
    else
        error "✗ Boot-time security script not found. Installation may have failed."
        exit 1
    fi
}

# Main installation procedure.
main() {
    log "Starting BlueCode Security Tools installation..."
    create_directories
    install_python_dependencies
    install_python_package
    setup_switch_button_script
    setup_boot_script
    setup_cli_command
    verify_installation

    echo ""
    log "Installation completed successfully!"
    echo ""
    echo "Usage instructions:"
    echo "- To run security randomization: bluecode [options]"
    echo "- For help: bluecode --help"
    echo "- To enable boot-time service: /etc/init.d/gl-mac-security enable"
    echo "- To start boot-time service: /etc/init.d/gl-mac-security start"
    echo ""
    echo "IMPORTANT: IMEI randomization requires a manual reboot."
    echo "Use 'bluecode --randomize imei --no-reboot-imei' for IMEI changes without automatic reboot."
}

main
