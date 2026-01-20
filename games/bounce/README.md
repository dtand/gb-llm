# Bounce

> Animated bouncing ball with sprite animation frames.

## Prompt

The exact prompt that should generate this game:

```
Create a simple demo with an animated bouncing ball. The ball sprite cycles through animation frames while bouncing around the screen. Use D-pad to change ball direction.
```

## How to Play

| Control | Action |
|---------|--------|
| D-Pad | Push ball in direction |
| START | Reset ball to center |

## Game Rules

- Ball bounces off screen edges
- Animation plays continuously
- D-pad applies force to ball

## Technical Notes

### Animation System
- 4-frame sprite animation
- Frame counter increments each game frame
- Animation frame = (frame_counter / 8) % 4
- Smooth looping animation

### Sprites Used
- Sprite 0: Ball (animated, 4 frames)
- **Total: 1 sprite, 4 tile frames**

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
| `game.h` | Ball state, animation constants |
| `game.c` | Movement, bounce, animation logic |
| `sprites.h` | Sprite definitions |
| `sprites.c` | Animation frame tile data |
