# Maze Sample Makefile
# Demonstrates procedural maze generation

GBDK = /usr/local/gbdk
CC = $(GBDK)/bin/lcc
CFLAGS = -Wa-l -Wl-m -Wl-j -Wm-yn"maze"

ROM_NAME = maze.gb
BUILD_DIR = build

# Automatically compile all .c files in src/
SRCS = $(wildcard src/*.c)
OBJS = $(SRCS:.c=.o)

all: $(BUILD_DIR) $(BUILD_DIR)/$(ROM_NAME)
	@echo ""
	@echo "Build complete: $(BUILD_DIR)/$(ROM_NAME)"
	@ls -la $(BUILD_DIR)/$(ROM_NAME)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/$(ROM_NAME): $(SRCS)
	$(CC) $(CFLAGS) -o $@ $^

clean:
	rm -rf $(BUILD_DIR)
	rm -f src/*.o src/*.lst src/*.sym src/*.asm

run: $(BUILD_DIR)/$(ROM_NAME)
	open -a SameBoy $(BUILD_DIR)/$(ROM_NAME)

run-mgba: $(BUILD_DIR)/$(ROM_NAME)
	mgba $(BUILD_DIR)/$(ROM_NAME)

rebuild: clean all

.PHONY: all clean run run-mgba rebuild
