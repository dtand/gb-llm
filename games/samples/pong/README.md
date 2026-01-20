# Pong

> Classic Pong arcade game with single-player vs AI opponent.

## Prompt

The exact prompt that should generate this game:

```
Create a Pong game with two paddles, a bouncing ball, and a simple AI opponent. The player controls the left paddle with the D-pad. First to 5 points wins.
```

## How to Play

| Control | Action |
|---------|--------|
| D-Pad Up | Move paddle up |
| D-Pad Down | Move paddle down |
| START | Pause/unpause game |
| START (game over) | Restart game |

## Game Rules

- Ball bounces off top and bottom walls
- Ball bounces off paddles
- Ball speeds up slightly after each paddle hit (max 3x)
- Score a point when ball passes opponent's paddle
- First to 5 points wins

## Technical Notes

### Sprites Used
- Sprite 0: Ball (8x8)
- Sprites 1-3: Left paddle (8x24, 3 tiles)
- Sprites 4-6: Right paddle (8x24, 3 tiles)
- **Total: 7 sprites**

### Collision Detection
Uses AABB (Axis-Aligned Bounding Box) collision:
- Ball checks overlap with paddle rectangles
- Wall bounce on Y boundaries

### AI Behavior
- AI paddle follows ball's Y position
- Throttled to update every 2 frames (makes it beatable)
- Has dead zone of ±4 pixels before moving

### Sound
- Single beep on all collisions (wall and paddle)
- Uses channel 1 square wave

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
| `game.h` | Game state structure, constants |
| `game.c` | Core logic: input, physics, AI |
| `sprites.h` | Sprite/tile index definitions |
| `sprites.c` | Sprite tile data, initialization |
