# BlueCode

# Overview

BlueCode Security Tools is a comprehensive Python-based toolkit designed to enhance anonymity and reduce forensic traceability on GL-iNet router devices, including support for GL-iNet Mudi v2. The toolkit focuses on randomizing various network identifiers and implementing anti-forensic measures to protect user privacy.

## Installation

### Getting Started

The toolkit is installed using the `install.sh` script:

```bash
# Update package lists
opkg update

# Make the install script executable
chmod +x ./install.sh

# Run the installation script
./install.sh
```

## Usage

### Basic Randomization

```bash
# Randomize all identifiers
sudo bluecode

# Randomize specific identifiers
sudo bluecode --randomize mac bssid
```

### View Current Identifiers

```bash
# Display all current identifiers
sudo bluecode info

# Display specific identifiers
sudo bluecode info mac imei
```

### Advanced Options

```bash
# Test changes without applying them
sudo bluecode --dry-run

# Randomize IMEI without automatic reboot
sudo bluecode --randomize imei --no-reboot-imei

# Randomize only WAN interface MAC address
sudo bluecode --randomize mac --interfaces wan
```

## Command-Line Interface

The CLI interface is implemented in `cli.py` and provides several subcommands and options:

### Main Commands

- **`bluecode secure`**: Run with randomization options (backward compatibility)
- **`bluecode info`**: Display current network identifiers
- **`bluecode`**: Default command (equivalent to randomize all identifiers)

### Key Options

- **`--randomize`**: Specify what to randomize (mac, bssid, imei, logs, all)
- **`--interfaces`**: Specify interfaces to randomize (wan, upstream, all)
- **`--dry-run`**: Simulate actions without making changes
- **`--no-restart`**: Do not restart network after changes
- **`--no-reboot-imei`**: Do not reboot after IMEI randomization
- **`--device-index`**: Specific device index to use for WAN interface
- **`--verbose`**: Enable verbose logging

## System Components

### Core Modules

1. **`bssid.py`**: Manages BSSID randomization for wireless interfaces
2. **`logs.py`**: Implements comprehensive log management with anti-forensic measures
3. **`mac.py`**: Handles MAC address randomization for network interfaces
4. **`modem.py`**: Controls modem hardware state and IMEI modifications
5. **`network.py`**: Manages network device configuration
6. **`sim.py`**: Detects and manages SIM card information
7. **`system.py`**: Provides system command execution utilities

### Utility Modules

1. **`generators.py`**: Contains MAC and IMEI generation algorithms
2. **`logger.py`**: Implements a singleton logger for consistent logging

### Configuration Files

1. **`50-toggle_wireless`**: Hotplug script for WiFi button functionality
2. **`boot.template`**: Init script template for boot-time security measures
3. **`install.sh`**: Main installation script

## Key Features

### Network Identifier Randomization

1. **MAC Address Randomization**

   - Randomizes MAC addresses for WAN and upstream interfaces
   - Generates valid, locally-administered unicast MAC addresses
   - Preserves network connectivity while changing identifiers

2. **BSSID Randomization**

   - Changes wireless BSSIDs (MAC addresses for WiFi interfaces)
   - Applies changes to both 2.4GHz and 5GHz access points
   - Preserves network settings while changing identifiers

3. **IMEI Randomization**
   - Generates valid IMEI numbers using the Luhn algorithm
   - Supports common manufacturer Type Allocation Codes (TACs)
   - Manages cellular modem state during IMEI changes

### Anti-Forensic Measures

1. **Log Management**

   - Identifies and sanitizes MAC addresses in log files
   - Uses secure deletion techniques (multi-pass overwriting)
   - Sets up tmpfs (RAM-only) storage for sensitive databases

2. **Boot-Time Security**

   - Initializes security measures at system boot
   - Implements RAM-only storage for client databases
   - Prevents persistence of identifying information

3. **Physical Button Integration**
   - Provides WiFi toggle functionality while preserving WAN connectivity
   - Allows quick disabling of local access points for additional privacy

## Security Considerations

1. **Boot-Time Security**: The init script must be properly installed and enabled to ensure security measures persist across reboots.

2. **IMEI Randomization**: Requires a reboot to take effect; can be performed without automatic reboot using the `--no-reboot-imei` option.

3. **Anti-Forensic Measures**: The toolkit implements several anti-forensic techniques, including secure deletion, RAM-only storage, and log sanitization.

4. **Authentication**: All commands require root privileges due to the system-level changes performed.

## File Structure

```
bluecode/
├── __init__.py         # Package initialization
├── cli.py              # Command-line interface
├── core/               # Core functionality
│   ├── __init__.py
│   ├── bssid.py        # BSSID randomization
│   ├── logs.py         # Log management
│   ├── mac.py          # MAC address randomization
│   ├── modem.py        # Modem control
│   ├── network.py      # Network configuration
│   ├── sim.py          # SIM card management
│   └── system.py       # System command execution
└── utils/              # Utility functions
    ├── __init__.py
    ├── generators.py   # MAC and IMEI generation
    └── logger.py       # Logging utilities

config/
├── hotplug/            # Hotplug scripts
│   └── 50-toggle_wireless
└── init.d/             # Init scripts
    ├── boot.template
    └── boot.template.sh

scripts/
└── bluecode            # Main executable wrapper
```

## Technical Details

### MAC Address Generation

The toolkit generates MAC addresses with the locally administered bit set, ensuring they don't conflict with manufacturer-assigned addresses. This approach adheres to IEEE standards while maintaining uniqueness.

### IMEI Generation

IMEI numbers are generated according to the standard format:

- First 8 digits: Type Allocation Code (TAC)
- Next 6 digits: Serial number
- Last digit: Check digit (calculated using the Luhn algorithm)

The generator can use common TACs for popular manufacturers or generate completely random ones.

### Anti-Forensic Techniques

The log management system implements several anti-forensic techniques:

- Secure deletion using multi-pass overwriting
- RAM-only storage using tmpfs mounts
- Log file sanitization to remove MAC addresses
- System buffer clearing
- File system journal flushing
