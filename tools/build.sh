#!/bin/bash
# Build a game project

GAME_DIR=$1

if [ -z "$GAME_DIR" ]; then
    echo "Usage: build.sh <game-directory>"
    echo "Example: build.sh ../games/pong"
    exit 1
fi

# Resolve to absolute path
GAME_DIR=$(cd "$GAME_DIR" 2>/dev/null && pwd)

if [ ! -d "$GAME_DIR" ]; then
    echo "Error: Directory not found: $GAME_DIR"
    exit 1
fi

if [ ! -f "$GAME_DIR/Makefile" ]; then
    echo "Error: No Makefile found in $GAME_DIR"
    exit 1
fi

echo "Building $(basename $GAME_DIR)..."

cd "$GAME_DIR"

# Clean previous build
make clean 2>/dev/null || true

# Build
if make; then
    echo ""
    echo "✓ Build successful!"
    ls -la build/*.gb 2>/dev/null || echo "ROM file created"
    exit 0
else
    echo ""
    echo "✗ Build failed!"
    exit 1
fi
