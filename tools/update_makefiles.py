#!/usr/bin/env python3
"""Update all sample Makefiles with schema and symbols generation."""

from pathlib import Path

SAMPLES_DIR = Path(__file__).parent.parent / "games" / "samples"

TEMPLATE = '''# {title} - GameBoy ROM Makefile

PROJECT = {project}
GBDK = $(GBDK_HOME)
LCC = $(GBDK)/bin/lcc

# Tools (set GBLLM_ROOT or use relative path)
GBLLM_ROOT ?= ../../..
SCHEMA_GEN = python3 $(GBLLM_ROOT)/tools/gen_schema.py
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

all: schema datagen $(ROM) symbols

# Generate _schema.json from @config annotations in headers
schema:
	@$(SCHEMA_GEN) src/ _schema.json

# Generate data.c/data.h from _schema.json (if exists)
datagen: schema
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

.PHONY: all clean run run-mgba rebuild schema datagen symbols
'''

def main():
    for sample_dir in sorted(SAMPLES_DIR.iterdir()):
        if sample_dir.is_dir():
            makefile = sample_dir / "Makefile"
            if makefile.exists():
                project = sample_dir.name
                title = project.replace('_', ' ').title()
                content = TEMPLATE.format(project=project, title=title)
                makefile.write_text(content)
                # Ensure context directory exists
                (sample_dir / "context").mkdir(exist_ok=True)
                print(f"Updated: {project}")
    print("Done!")

if __name__ == "__main__":
    main()
