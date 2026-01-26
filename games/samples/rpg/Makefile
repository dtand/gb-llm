# RPG - GameBoy ROM Makefile

PROJECT = rpg
GBDK = $(GBDK_HOME)
LCC = $(GBDK)/bin/lcc

# Data generator (set GBLLM_ROOT or use relative path)
GBLLM_ROOT ?= ../../..
DATA_GEN = python3 $(GBLLM_ROOT)/src/generator/data_generator.py

CFLAGS = -Wa-l -Wl-m -Wl-j -Wm-yn"$(PROJECT)"
SOURCES = src/main.c src/game.c src/sprites.c
BUILD_DIR = build
ROM = $(BUILD_DIR)/$(PROJECT).gb

# Include data.c if schema exists
ifneq ($(wildcard _schema.json),)
DATA_SRC = build/data.c
endif

all: datagen $(ROM)

# Generate data.c/data.h from _schema.json (if exists)
datagen:
	@if [ -f _schema.json ]; then $(DATA_GEN) .; fi

$(ROM): $(SOURCES) datagen
	@mkdir -p $(BUILD_DIR)
	$(LCC) $(CFLAGS) -o $(ROM) $(SOURCES) $(DATA_SRC)
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

.PHONY: all clean run run-mgba rebuild datagen
