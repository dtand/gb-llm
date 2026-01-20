# Snake

> Classic Snake arcade game - eat food to grow, avoid hitting yourself.

## Prompt

The exact prompt that should generate this game:

```
Create a Snake game where the player controls a snake that moves around the screen eating food. Each food item makes the snake grow longer. The game ends if the snake hits itself or the wall. Use D-pad for direction control.
```

## How to Play

| Control | Action |
|---------|--------|
| D-Pad | Change snake direction |
| START | Pause/unpause game |
| START (game over) | Restart game |

## Game Rules

- Snake moves continuously in current direction
- Eating food grows the snake by one segment
- New food spawns randomly after eating
- Game over if snake hits wall or itself
- Score increases with each food eaten

## Technical Notes

### Sprites Used
- Sprites 0-9: Snake body segments (max 10 visible at once)
- Sprite 10: Food
- **Total: 11 sprites max** (uses sprite cycling for longer snakes)

### Movement System
- Grid-based movement (8x8 pixel steps)
- Movement throttled to every 8 frames for playable speed
- Direction change buffered to prevent 180° turns

### Collision Detection
- Wall collision: check against screen boundaries
- Self collision: check head against all body segments
- Food collision: check head overlap with food position

### Random Number Generation
- Uses frame counter + button presses for seed
- LCG (Linear Congruential Generator) for food placement

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
| `game.h` | Game state, constants, snake data structure |
| `game.c` | Core logic: movement, collision, food |
| `sprites.h` | Sprite/tile index definitions |
| `sprites.c` | Sprite tile data, initialization |
