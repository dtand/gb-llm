# Adventure - GameBoy ROM Makefile

PROJECT = adventure
GBDK = $(GBDK_HOME)
LCC = $(GBDK)/bin/lcc

# Tools (set GBLLM_ROOT or use relative path)
GBLLM_ROOT ?= ../../..
DATA_GEN = python3 $(GBLLM_ROOT)/src/generator/data_generator.py
SYMBOL_GEN = python3 $(GBLLM_ROOT)/tools/gen_symbols.py

CFLAGS = -Wa-l -Wl-m -Wl-j -Wm-yn"$(PROJECT)"
SOURCES = $(wildcard src/*.c)
BUILD_DIR = build
ROM = $(BUILD_DIR)/$(PROJECT).gb
SYMBOLS = context/symbols.json

# Include data.c if schema exists
ifneq ($(wildcard _schema.json),)
DATA_SRC = build/data.c
endif

all: datagen $(ROM) symbols

# Generate data.c/data.h from _schema.json (if exists)
datagen:
	@if [ -f _schema.json ]; then $(DATA_GEN) .; fi

# Generate symbol index for AI agents
symbols: $(SOURCES)
	@mkdir -p context
	@$(SYMBOL_GEN) src context/symbols.json

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

.PHONY: all clean run run-mgba rebuild datagen symbols
