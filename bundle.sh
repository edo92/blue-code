#!/bin/bash
set -e

echo "Creating offline package bundle for BlueCode..."

# Create directories
mkdir -p bluecode-bundle
mkdir -p bluecode-bundle/pip_packages

# Download pip packages
echo "Downloading pip packages..."
pip3 download pyserial -d bluecode-bundle/pip_packages

# Copy BlueCode files
echo "Copying BlueCode files..."
cp -r bluecode bluecode-bundle/
cp -r config bluecode-bundle/
cp -r scripts bluecode-bundle/
cp setup.py bluecode-bundle/
cp LICENSE bluecode-bundle/
cp README.md bluecode-bundle/
cp MANIFEST.in bluecode-bundle/

# Add offline installation script
cp offline-install.sh bluecode-bundle/

# Create tar archive for easy transfer
tar -czf bluecode-offline.tar.gz bluecode-bundle
rm -rf ./bluecode-bundle

echo "Bundle created as bluecode-offline.tar.gz"
echo "Transfer this file to your GL-iNet device and extract it with:"
echo "tar -xzf bluecode-offline.tar.gz"
echo "Then run: cd bluecode-bundle && ./offline-install.sh"
