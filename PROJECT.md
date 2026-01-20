# GB-LLM: GameBoy ROM Generator

> An LLM-powered system that generates compilable GameBoy ROMs from natural language descriptions.

## Vision

Transform natural language game descriptions into fully functional GameBoy ROMs through an iterative, human-in-the-loop development process.

## Goals

1. **Generate working GameBoy games** from plain English descriptions
2. **Start simple, scale up** - Begin with Pong/Snake, expand to more complex games
3. **Iterative refinement** - Human plays in emulator, provides feedback, agent improves
4. **Clean, maintainable output** - Generated code should be readable and well-structured

## Scope

### Phase 1: Foundation (Current)
- [ ] Project architecture and documentation
- [ ] Toolchain setup (GBDK-2020, emulator integration)
- [ ] First working game: Pong
- [ ] Basic feedback loop established

### Phase 2: Simple Games
- [ ] Snake
- [ ] Breakout
- [ ] Tetris clone
- [ ] Template library for common patterns

### Phase 3: Expansion
- [ ] Sprite/tile editor integration
- [ ] Sound/music generation
- [ ] More complex game types (platformer, puzzle)
- [ ] Multi-level game support

## Key Principles

1. **Compilation is mandatory** - Every generated ROM must compile successfully
2. **Playability matters** - Games must be functional, not just compile
3. **Feedback drives improvement** - Human testing informs iterations
4. **Constraints breed creativity** - GB limitations are features, not bugs

## Project Structure

```
gb-llm/
├── PROJECT.md              # This file - project overview
├── docs/                   # Design documents
│   ├── ARCHITECTURE.md     # System design
│   ├── GAMEBOY_SPECS.md    # Hardware reference
│   ├── GENERATION_STRATEGY.md  # Code generation approach
│   ├── TOOLCHAIN.md        # Build tools & workflow
│   └── GAME_PATTERNS.md    # Reusable game templates
├── src/                    # Generator source code
│   ├── generator/          # LLM integration & prompts
│   ├── templates/          # Code templates
│   └── validator/          # Compilation & validation
├── games/                  # Generated game projects
│   └── {game-name}/        # Individual game folders
│       ├── src/            # Game source code
│       ├── assets/         # Sprites, tiles, sounds
│       └── build/          # Compiled ROM output
└── tools/                  # Build scripts & utilities
```

## Success Criteria

A successful v1.0 will:
- Generate a playable Pong game from a single prompt
- Support iterative refinement through natural feedback
- Produce ROMs that run on real GameBoy hardware (via flashcart)
- Have clear documentation for extending to new game types

## Links

- [Architecture](docs/ARCHITECTURE.md)
- [GameBoy Specs](docs/GAMEBOY_SPECS.md)
- [Generation Strategy](docs/GENERATION_STRATEGY.md)
- [Toolchain](docs/TOOLCHAIN.md)
- [Game Patterns](docs/GAME_PATTERNS.md)
