# Runner

> Simple endless runner with horizontal scrolling background.

## Prompt

The exact prompt that should generate this game:

```
Create a simple endless runner where a character automatically runs right while the background scrolls. The player presses A to jump over obstacles. Score increases over time. Game ends when hitting an obstacle.
```

## How to Play

| Control | Action |
|---------|--------|
| A Button | Jump |
| START | Restart after game over |

## Game Rules

- Character runs automatically (background scrolls left)
- Press A to jump over obstacles
- Score increases each frame survived
- Game over on obstacle collision

## Technical Notes

### Scrolling System
- Uses hardware scroll registers (SCX)
- Background wraps at 256 pixels (32 tiles)
- Obstacles placed in background tile map
- SCX incremented each frame for smooth scroll

### Sprites Used
- Sprite 0: Player character
- **Total: 1 sprite**

### Background
- Repeating ground pattern
- Obstacles as background tiles (not sprites)

## Build

```bash
make        # Build ROM
make run    # Build and launch in SameBoy
make clean  # Remove build artifacts
```

## Files

| File | Purpose |
|------|---------|
| `main.c` | Entry point, game loop |
| `game.h` | Game state, scroll position |
| `game.c` | Core logic: scrolling, jump, collision |
| `sprites.h` | Sprite/tile index definitions |
| `sprites.c` | Tile data for player and background |
