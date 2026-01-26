# GB-LLM

> Generate playable GameBoy ROMs from natural language descriptions.

## Overview

GB-LLM transforms plain English game descriptions into fully functional GameBoy ROMs through an iterative, human-in-the-loop development process. It uses a multi-agent pipeline (Designer → Coder → Reviewer) powered by Claude to analyze requests, implement features, and validate code.

## Quick Start

### 1. Prerequisites

**Required:**
- macOS (or Linux with modifications)
- Python 3.11+
- [GBDK-2020](https://github.com/gbdk-2020/gbdk-2020) - GameBoy C compiler
- [Anthropic API key](https://console.anthropic.com/)

**For Playing ROMs:**
- [SameBoy](https://sameboy.github.io/) (recommended) or [mGBA](https://mgba.io/)

### 2. Install GBDK-2020

```bash
# Download latest release from GitHub
# https://github.com/gbdk-2020/gbdk-2020/releases

# Extract to /usr/local/gbdk (or update Makefile paths)
sudo tar -xzf gbdk-4.x.x-macos.tar.gz -C /usr/local/

# Verify installation
/usr/local/gbdk/bin/lcc --version
```

### 3. Set Up Python Environment

```bash
# Clone the repository
git clone https://github.com/your-username/gb-llm.git
cd gb-llm

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"
# Or add to ~/.zshrc / ~/.bashrc for persistence
```

### 4. Launch the Web App

```bash
# Activate virtual environment (if not already)
source .venv/bin/activate

# Start the server
cd src/web
python api.py

# Open in browser
# http://localhost:8000
```

The web interface allows you to:
- Create new game projects (from scratch or templates)
- Chat with the AI to design features
- Build and iterate on your game
- Play ROMs directly in the browser emulator
- Tune game parameters in real-time

### 5. Run ROMs Locally

```bash
# Using SameBoy (recommended)
open -a SameBoy path/to/game.gb

# Using mGBA
open -a mGBA path/to/game.gb

# Or use the build script for sample games
cd games/samples/pong
make run
```

## Project Structure

```
gb-llm/
├── docs/               # Design documentation
├── src/
│   ├── agents/         # LLM agents (Designer, Coder, Reviewer)
│   │   ├── pipeline/   # Orchestrates multi-agent workflow
│   │   ├── designer/   # Analyzes requests, plans features
│   │   ├── coder/      # Implements code changes
│   │   └── reviewer/   # Validates code quality
│   ├── corpus/         # Vector search for code patterns
│   ├── web/            # FastAPI server + web UI
│   └── templates/      # Code templates
├── games/
│   ├── samples/        # 20 example games (pong, snake, rpg, etc.)
│   ├── projects/       # User-created projects
│   └── corpus_db/      # Indexed code patterns
└── tools/              # Build scripts
```

## Sample Games

The `games/samples/` directory contains 20 working example games:

| Game | Description |
|------|-------------|
| pong | Classic paddle game |
| snake | Growing snake game |
| breakout | Brick breaker |
| platformer | Side-scrolling platformer |
| shooter | Space shooter |
| rpg | Turn-based RPG with battles |
| puzzle | Sliding puzzle |
| racing | Top-down racing |
| ... | And 12 more! |

Build any sample:
```bash
cd games/samples/snake
make
make run
```

## Documentation

- [PROJECT.md](PROJECT.md) - Project vision and roadmap
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
- [docs/GAMEBOY_SPECS.md](docs/GAMEBOY_SPECS.md) - Hardware reference
- [docs/TOOLCHAIN.md](docs/TOOLCHAIN.md) - Build tools setup
- [docs/GAME_PATTERNS.md](docs/GAME_PATTERNS.md) - Reusable code templates
- [docs/CODE_STANDARDS.md](docs/CODE_STANDARDS.md) - Coding conventions

## Troubleshooting

**Build fails with "lcc not found":**
- Ensure GBDK-2020 is installed at `/usr/local/gbdk`
- Or update the `GBDK` path in your project's Makefile

**API errors:**
- Check that `ANTHROPIC_API_KEY` is set
- Verify your API key has available credits

**Port 8000 in use:**
```bash
lsof -ti:8000 | xargs kill -9
```

## License

MIT
