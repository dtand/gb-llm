# Development Toolchain

## Overview

This document describes the tools required to compile GameBoy ROMs and test them, plus the integration points for the generation system.

## Required Tools

### 1. GBDK-2020 (Compiler)

**What:** Modern fork of the original GameBoy Development Kit, providing a C compiler targeting the GameBoy.

**Installation:**

```bash
# macOS (Homebrew)
brew install gbdk-2020

# Or download from GitHub releases
# https://github.com/gbdk-2020/gbdk-2020/releases

# Extract to /opt/gbdk (or preferred location)
tar -xzf gbdk-4.2.0-macos.tar.gz -C /opt/

# Add to PATH
export GBDK=/opt/gbdk
export PATH=$PATH:$GBDK/bin
```

**Verify Installation:**
```bash
lcc --version
# Should output: lcc version X.X.X
```

**Key Binaries:**
| Binary | Purpose |
|--------|---------|
| `lcc` | Main compiler driver |
| `sdcc` | Underlying C compiler |
| `sdasgb` | Assembler |
| `sdldgb` | Linker |
| `makebin` | ROM generator |

### 2. Emulator (Testing)

**Primary: SameBoy** (macOS native, accurate)
```bash
brew install --cask sameboy
```

**Alternative: mGBA** (cross-platform)
```bash
brew install mgba
```

**Alternative: BGB** (Windows, best debugging - use with Wine)
```bash
brew install --cask wine-stable
# Download BGB from https://bgb.bircd.org/
```

**Emulator Comparison:**

| Feature | SameBoy | mGBA | BGB |
|---------|---------|------|-----|
| Accuracy | ★★★★★ | ★★★★☆ | ★★★★★ |
| Debugging | ★★★☆☆ | ★★★☆☆ | ★★★★★ |
| macOS Native | ✓ | ✓ | ✗ (Wine) |
| Ease of Use | ★★★★★ | ★★★★☆ | ★★★☆☆ |

**Recommendation:** Use SameBoy for quick testing, BGB when deep debugging is needed.

### 3. Graphics Tools

**GBTD/GBMB** (Tile/Map Designer)
- Classic tools, Windows only (Wine)
- Good for hand-crafting tiles

**Aseprite** (Sprite Editor)
```bash
# Commercial software, available on Steam or itch.io
# Export to PNG, convert with tools below
```

**png2asset** (Included with GBDK-2020)
```bash
# Convert PNG to C source
png2asset sprite.png -o sprite.c
```

### 4. Build Automation

**Make** (Standard)
```bash
# Usually pre-installed on macOS
make --version
```

**Example Makefile:**
```makefile
# GBDK-2020 Makefile Template

# Paths
GBDK = /opt/gbdk
CC = $(GBDK)/bin/lcc
CFLAGS = -Wa-l -Wl-m -Wl-j

# Project
PROJECT = mygame
SOURCES = src/main.c src/game.c src/sprites.c
OBJECTS = $(SOURCES:.c=.o)

# Output
ROMNAME = $(PROJECT).gb

# Targets
all: $(ROMNAME)

$(ROMNAME): $(OBJECTS)
	$(CC) $(CFLAGS) -o build/$(ROMNAME) $(OBJECTS)

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJECTS) build/$(ROMNAME)

run: $(ROMNAME)
	open -a SameBoy build/$(ROMNAME)

.PHONY: all clean run
```

## Directory Structure

```
gb-llm/
├── tools/
│   ├── setup.sh           # Environment setup script
│   ├── build.sh           # Build wrapper script
│   ├── run.sh             # Launch emulator script
│   └── convert_sprite.sh  # PNG to sprite converter
└── games/
    └── {game}/
        ├── Makefile
        ├── src/
        ├── assets/
        └── build/
```

## Environment Setup

### setup.sh
```bash
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
if ! command -v sameboy &> /dev/null; then
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
```

## Build Workflow

### Compilation Pipeline

```
Source Files (.c)
       │
       ▼
   ┌───────┐
   │  lcc  │  (Compiler driver)
   └───┬───┘
       │
       ▼
   ┌───────┐
   │ sdcc  │  (C to assembly)
   └───┬───┘
       │
       ▼
   ┌───────┐
   │sdasgb │  (Assembly to object)
   └───┬───┘
       │
       ▼
   ┌───────┐
   │sdldgb │  (Linker)
   └───┬───┘
       │
       ▼
   ┌───────┐
   │makebin│  (Create ROM)
   └───┬───┘
       │
       ▼
   ROM File (.gb)
```

### build.sh
```bash
#!/bin/bash
# Build a game project

GAME_DIR=$1

if [ -z "$GAME_DIR" ]; then
    echo "Usage: build.sh <game-directory>"
    exit 1
fi

cd "$GAME_DIR"

echo "Building $(basename $GAME_DIR)..."

# Clean previous build
make clean 2>/dev/null || true

# Build
if make; then
    echo "✓ Build successful!"
    ls -la build/*.gb
    exit 0
else
    echo "✗ Build failed!"
    exit 1
fi
```

### run.sh
```bash
#!/bin/bash
# Run a ROM in the emulator

ROM_FILE=$1
EMULATOR=${2:-sameboy}

if [ -z "$ROM_FILE" ]; then
    echo "Usage: run.sh <rom-file> [emulator]"
    echo "Emulators: sameboy, mgba, bgb"
    exit 1
fi

case $EMULATOR in
    sameboy)
        open -a SameBoy "$ROM_FILE"
        ;;
    mgba)
        mgba "$ROM_FILE"
        ;;
    bgb)
        wine ~/.wine/drive_c/bgb/bgb.exe "$ROM_FILE"
        ;;
    *)
        echo "Unknown emulator: $EMULATOR"
        exit 1
        ;;
esac
```

## Asset Pipeline

### PNG to Sprite Conversion

```bash
# Using png2asset (GBDK-2020)
png2asset input.png \
    -c output.c \
    -sw 8 -sh 8 \          # Sprite width/height
    -spr8x8                 # 8x8 sprite mode
```

### Sprite Requirements

| Property | Requirement |
|----------|-------------|
| Colors | Max 4 (including transparent) |
| Dimensions | Multiple of 8 pixels |
| Format | PNG with indexed palette |
| Transparency | Color index 0 = transparent |

### Recommended Palette (DMG)
```
Color 0: #9BBC0F (Lightest / Transparent for sprites)
Color 1: #8BAC0F (Light)
Color 2: #306230 (Dark)
Color 3: #0F380F (Darkest)
```

## Integration Points

### For Generation System

The generator system needs to:

1. **Create project structure**
   ```python
   def create_game_project(name):
       # Create directories
       # Generate Makefile
       # Create source file stubs
   ```

2. **Compile and capture output**
   ```python
   def compile_game(game_dir):
       result = subprocess.run(
           ['make'],
           cwd=game_dir,
           capture_output=True,
           text=True
       )
       return {
           'success': result.returncode == 0,
           'stdout': result.stdout,
           'stderr': result.stderr
       }
   ```

3. **Launch emulator**
   ```python
   def launch_emulator(rom_path):
       subprocess.Popen(['open', '-a', 'SameBoy', rom_path])
   ```

4. **Parse compiler errors**
   ```python
   def parse_errors(stderr):
       # Extract file, line, error message
       # Return structured error list
   ```

## Troubleshooting

### Common Issues

**"lcc: command not found"**
- Ensure GBDK is in PATH
- Run: `export PATH=$PATH:/opt/gbdk/bin`

**"undefined reference to 'main'"**
- Check that main.c exists and has `void main(void)`

**ROM doesn't boot in emulator**
- Check ROM header (use validation tools)
- Ensure proper Nintendo logo in header

**Sprite not visible**
- Check sprite is enabled: `SHOW_SPRITES`
- Verify OAM is loaded correctly
- Check sprite Y position (0 = off screen)

**Out of memory errors**
- Reduce global variable count
- Move constant data to ROM with `const`
- Check for stack overflow

### Debug Techniques

**Using BGB Debugger:**
1. Load ROM in BGB
2. Press Escape for debugger
3. Set breakpoints on addresses
4. Step through code

**Adding Debug Output:**
```c
// Simple debug - write to unused memory
void debug_value(UINT8 val) {
    *((UINT8*)0xC000) = val;  // Check in debugger
}
```

## Version Requirements

| Tool | Minimum Version | Recommended |
|------|-----------------|-------------|
| GBDK-2020 | 4.0.0 | 4.2.0+ |
| SameBoy | 0.14 | Latest |
| mGBA | 0.9 | Latest |
| Make | 3.81 | Any |

## Resources

- [GBDK-2020 Documentation](https://gbdk-2020.github.io/gbdk-2020/docs/api/)
- [Pan Docs (GB Hardware)](https://gbdev.io/pandocs/)
- [Awesome Game Boy Dev](https://github.com/gbdev/awesome-gbdev)
- [GB Assembly Tutorial](https://eldred.fr/gb-asm-tutorial/)
