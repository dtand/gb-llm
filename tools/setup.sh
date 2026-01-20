#!/bin/bash
# GB-LLM Environment Setup

set -e

echo "=== GB-LLM Development Environment Setup ==="

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install GBDK-2020
if ! command -v lcc &> /dev/null; then
    echo "Installing GBDK-2020..."
    brew install gbdk-2020
fi

# Install emulator
if [ ! -d "/Applications/SameBoy.app" ]; then
    echo "Installing SameBoy..."
    brew install --cask sameboy
fi

# Install mGBA as backup
if ! command -v mgba &> /dev/null; then
    echo "Installing mGBA..."
    brew install mgba
fi

# Verify installations
echo ""
echo "=== Verification ==="
echo -n "lcc: "
lcc --version 2>/dev/null | head -1 || echo "NOT FOUND"
echo -n "SameBoy: "
[ -d "/Applications/SameBoy.app" ] && echo "Installed" || echo "NOT FOUND"
echo -n "mGBA: "
mgba --version 2>/dev/null | head -1 || echo "NOT FOUND"

echo ""
echo "=== Setup Complete ==="
