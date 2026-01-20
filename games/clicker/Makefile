# Clicker - GameBoy ROM Makefile

PROJECT = clicker
GBDK = $(GBDK_HOME)
LCC = $(GBDK)/bin/lcc
# Enable MBC1+RAM+BATTERY for save support
CFLAGS = -Wa-l -Wl-m -Wl-j -Wm-yn"$(PROJECT)" -Wm-yc -Wm-ya1
SOURCES = src/main.c src/game.c src/sprites.c
BUILD_DIR = build
ROM = $(BUILD_DIR)/$(PROJECT).gb

all: $(ROM)

$(ROM): $(SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(LCC) $(CFLAGS) -o $(ROM) $(SOURCES)
	@echo ""
	@echo "Build complete: $(ROM)"
	@ls -la $(ROM)

clean:
	rm -rf $(BUILD_DIR)
	rm -f src/*.o src/*.lst src/*.sym src/*.asm

run: $(ROM)
	open -a SameBoy $(ROM)

run-mgba: $(ROM)
	mgba $(ROM)

rebuild: clean all

.PHONY: all clean run run-mgba rebuild
