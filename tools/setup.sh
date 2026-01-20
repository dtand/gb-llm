#!/bin/bash
# GB-LLM Environment Setup

set -e

echo "=== GB-LLM Development Environment Setup ==="

# Configuration
GBDK_VERSION="4.5.0"
GBDK_INSTALL_DIR="/usr/local/gbdk"

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install GBDK-2020 from GitHub releases
if [ ! -d "$GBDK_INSTALL_DIR" ] || [ ! -f "$GBDK_INSTALL_DIR/bin/lcc" ]; then
    echo "Installing GBDK-2020 v${GBDK_VERSION}..."
    
    # Determine architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        GBDK_ARCHIVE="gbdk-macos-arm64.tar.gz"
    else
        GBDK_ARCHIVE="gbdk-macos.tar.gz"
    fi
    
    GBDK_URL="https://github.com/gbdk-2020/gbdk-2020/releases/download/${GBDK_VERSION}/${GBDK_ARCHIVE}"
    
    echo "Downloading from $GBDK_URL..."
    
    # Download and extract
    TEMP_DIR=$(mktemp -d)
    curl -L "$GBDK_URL" -o "$TEMP_DIR/gbdk.tar.gz"
    
    echo "Extracting..."
    tar -xzf "$TEMP_DIR/gbdk.tar.gz" -C "$TEMP_DIR"
    
    # Install (may need sudo)
    echo "Installing to $GBDK_INSTALL_DIR (may require password)..."
    sudo rm -rf "$GBDK_INSTALL_DIR"
    sudo mv "$TEMP_DIR/gbdk" "$GBDK_INSTALL_DIR"
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    
    echo "GBDK-2020 installed to $GBDK_INSTALL_DIR"
else
    echo "GBDK-2020 already installed at $GBDK_INSTALL_DIR"
fi

# Add to PATH hint
if [[ ":$PATH:" != *":$GBDK_INSTALL_DIR/bin:"* ]]; then
    echo ""
    echo "NOTE: Add GBDK to your shell configuration by adding these lines to ~/.zshrc:"
    echo "  export GBDK_HOME=$GBDK_INSTALL_DIR"
    echo "  export PATH=\"\$PATH:$GBDK_INSTALL_DIR/bin\""
    echo ""
    
    # Offer to add automatically
    read -p "Would you like to add these to ~/.zshrc now? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "" >> ~/.zshrc
        echo "# GBDK-2020 GameBoy Development Kit" >> ~/.zshrc
        echo "export GBDK_HOME=$GBDK_INSTALL_DIR" >> ~/.zshrc
        echo "export PATH=\"\$PATH:$GBDK_INSTALL_DIR/bin\"" >> ~/.zshrc
        echo "Added to ~/.zshrc. Run 'source ~/.zshrc' or open a new terminal."
    fi
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
