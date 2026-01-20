# Breakout

> Classic brick-breaking arcade game - bounce the ball to destroy all bricks.

## Prompt

The exact prompt that should generate this game:

```
Create a Breakout game with a paddle, bouncing ball, and rows of destructible bricks. The player controls the paddle with D-pad left/right. Clear all bricks to win. The ball bounces off walls, paddle, and bricks. Lives decrease when ball falls below paddle.
```

## How to Play

| Control | Action |
|---------|--------|
| D-Pad Left/Right | Move paddle |
| START | Launch ball / Restart after game over |
| SELECT | (unused) |

## Game Rules

- Move paddle to bounce ball upward
- Ball destroys bricks on contact
- Different colored rows give different points
- 3 lives - lose one when ball falls below paddle
- Clear all bricks to win

## Technical Notes

### Background Tiles
- Uses background layer for bricks (efficient for many objects)
- 5 rows × 10 columns = 50 bricks maximum
- Brick destruction updates background tile map

### Sprites Used
- Sprite 0: Ball (8x8)
- Sprite 1-2: Paddle (16 pixels wide, 2 sprites)
- **Total: 3 sprites**

### Collision Detection
- Ball vs walls: boundary check
- Ball vs paddle: AABB with angle deflection
- Ball vs bricks: grid-based lookup in tile map

### Ball Physics
- Velocity stored as dx/dy (signed)
- Speed constant, direction changes on bounce
- Paddle hit position affects bounce angle

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
| `game.h` | Game state, brick layout, ball physics |
| `game.c` | Core logic: movement, collision, scoring |
| `sprites.h` | Sprite/tile index definitions |
| `sprites.c` | Sprite and background tile data |
