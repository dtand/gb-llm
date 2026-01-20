# GB-LLM

> Generate playable GameBoy ROMs from natural language descriptions.

## Overview

GB-LLM transforms plain English game descriptions into fully functional GameBoy ROMs through an iterative, human-in-the-loop development process.

## Quick Start

```bash
# 1. Set up development environment
./tools/setup.sh

# 2. Build a game
./tools/build.sh games/pong

# 3. Run in emulator
./tools/run.sh games/pong/build/pong.gb
```

## Project Structure

```
gb-llm/
├── docs/               # Design documentation
├── src/                # Generator source code
│   ├── generator/      # LLM integration
│   ├── templates/      # Code templates
│   └── validator/      # Build validation
├── games/              # Generated game projects
└── tools/              # Build scripts
```

## Documentation

- [PROJECT.md](PROJECT.md) - Project vision and roadmap
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
- [docs/GAMEBOY_SPECS.md](docs/GAMEBOY_SPECS.md) - Hardware reference
- [docs/GENERATION_STRATEGY.md](docs/GENERATION_STRATEGY.md) - Code generation approach
- [docs/TOOLCHAIN.md](docs/TOOLCHAIN.md) - Build tools setup
- [docs/GAME_PATTERNS.md](docs/GAME_PATTERNS.md) - Reusable code templates

## Requirements

- macOS (or Linux with modifications)
- [GBDK-2020](https://github.com/gbdk-2020/gbdk-2020) - GameBoy C compiler
- [SameBoy](https://sameboy.github.io/) or [mGBA](https://mgba.io/) - Emulator

## License

MIT
