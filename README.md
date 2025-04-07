# GL-iNet Privacy and Security Tools

A collection of privacy and security enhancement tools for GL-iNet routers.

## Features

- MAC Address Randomization
- BSSID Randomization
- IMEI Randomization (for routers with cellular modems)
- MAC address log wiping

## Installation

```bash
./install.sh
```

## Usage

```bash
# Randomize all identifiers
bluecode --randomize all

# Only randomize MAC addresses
bluecode --randomize mac

# Dry run to see what would happen
bluecode --randomize all --dry-run

# With verbose output
bluecode --randomize all --verbose
```

## Options

```
  --dry-run             Simulate actions without making changes
  --verbose, -v         Enable verbose logging
  --interfaces WAN UPSTREAM [WAN UPSTREAM ...]
                        Interfaces to randomize (default: wan upstream)
  --no-restart          Do not restart network after changes
  --device-index DEVICE_INDEX
                        Specific device index to use for WAN interface
  --randomize {mac,bssid,imei,logs,all} [{mac,bssid,imei,logs,all} ...]
                        What to randomize (default: mac)
```

## License

MIT
