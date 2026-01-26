# Falling Block Puzzle

A Tetris-style falling block puzzle game demonstrating **grid systems**, **piece rotation**, and **line clearing**.

## Features Demonstrated

- **Grid System**: 10x20 playfield stored as 2D array
- **Piece Rotation**: 4 rotation states per piece type
- **Line Clearing**: Detect and remove completed rows
- **Collision Detection**: Grid-based collision for pieces

## Controls

| Button | Action |
|--------|--------|
| D-Pad Left/Right | Move piece |
| D-Pad Down | Fast drop |
| A | Rotate piece |
| START | Restart after game over |

## Gameplay

1. Pieces fall from the top of the playfield
2. Move and rotate to fit pieces together
3. Complete horizontal lines to clear them
4. Game ends when pieces reach the top

## Technical Notes

### Grid System

The playfield is a 10-wide by 20-tall grid:
```c
uint8_t grid[GRID_HEIGHT][GRID_WIDTH];  // 0 = empty, 1 = filled
```

### Piece Representation

Each piece is defined as a 4x4 template with 4 rotation states:
```c
const uint8_t piece_I[4][4][4] = {
    // Rotation 0
    {{0,0,0,0}, {1,1,1,1}, {0,0,0,0}, {0,0,0,0}},
    // Rotation 1
    {{0,1,0,0}, {0,1,0,0}, {0,1,0,0}, {0,1,0,0}},
    // ... etc
};
```

### Collision Check

Before moving/rotating, check if new position is valid:
```c
uint8_t can_place(int8_t px, int8_t py, uint8_t rotation) {
    for (y = 0; y < 4; y++) {
        for (x = 0; x < 4; x++) {
            if (piece[rotation][y][x]) {
                // Check bounds and grid collision
                if (px + x < 0 || px + x >= GRID_WIDTH) return 0;
                if (py + y >= GRID_HEIGHT) return 0;
                if (grid[py + y][px + x]) return 0;
            }
        }
    }
    return 1;
}
```

### Line Clearing

After placing a piece, check each row:
```c
for (y = 0; y < GRID_HEIGHT; y++) {
    uint8_t full = 1;
    for (x = 0; x < GRID_WIDTH; x++) {
        if (!grid[y][x]) { full = 0; break; }
    }
    if (full) {
        // Shift all rows above down
        clear_line(y);
    }
}
```

## Build

```bash
make        # Build ROM
make run    # Build and run in SameBoy
make clean  # Remove build artifacts
```
