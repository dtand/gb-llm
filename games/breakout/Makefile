# Breakout - GameBoy ROM Makefile

# Project name
PROJECT = breakout

# GBDK path (uses GBDK_HOME environment variable)
GBDK = $(GBDK_HOME)
LCC = $(GBDK)/bin/lcc

# Compiler flags
CFLAGS = -Wa-l -Wl-m -Wl-j -Wm-yn"$(PROJECT)"

# Source files
SOURCES = src/main.c src/game.c src/sprites.c

# Build directory
BUILD_DIR = build

# Output ROM
ROM = $(BUILD_DIR)/$(PROJECT).gb

# Default target
all: $(ROM)

# Create build directory and compile
$(ROM): $(SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(LCC) $(CFLAGS) -o $(ROM) $(SOURCES)
	@echo ""
	@echo "Build complete: $(ROM)"
	@ls -la $(ROM)

# Clean build artifacts
clean:
	rm -rf $(BUILD_DIR)
	rm -f src/*.o src/*.lst src/*.sym src/*.asm

# Run in SameBoy emulator
run: $(ROM)
	open -a SameBoy $(ROM)

# Run in mGBA emulator
run-mgba: $(ROM)
	mgba $(ROM)

# Rebuild from scratch
rebuild: clean all

.PHONY: all clean run run-mgba rebuild
