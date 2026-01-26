# Top-Down Adventure

A simple adventure game demonstrating **tile-based maps**, **4-way movement**, and **NPC interaction**.

## Features Demonstrated

- **Tile Map**: 20x18 world stored as 2D array
- **4-Way Movement**: Grid-aligned player movement
- **Wall Collision**: Solid tiles block movement
- **NPC Interaction**: Talk to characters with A button
- **Dialog System**: Window layer displays messages

## Controls

| Button | Action |
|--------|--------|
| D-Pad | Move in 4 directions |
| A | Talk to nearby NPC |

## Gameplay

1. Explore the small village area
2. Walk up to the NPC (person sprite)
3. Press A to interact and see dialog
4. Walls and trees block movement

## Technical Notes

### Tile Map

World stored as tile indices:
```c
const uint8_t world_map[MAP_HEIGHT][MAP_WIDTH] = {
    {1,1,1,1,1,1,...},  // 1 = wall
    {1,0,0,0,2,0,...},  // 0 = floor, 2 = tree
    ...
};
```

### Collision Check

Before moving, check target tile:
```c
uint8_t get_tile(uint8_t tx, uint8_t ty) {
    return world_map[ty][tx];
}

uint8_t is_solid(uint8_t tile) {
    return (tile == TILE_WALL || tile == TILE_TREE);
}
```

### NPC Interaction

Check if player is adjacent to NPC:
```c
if (abs(player_x - npc_x) + abs(player_y - npc_y) == 1) {
    // Player is next to NPC
    show_dialog("Hello traveler!");
}
```

### Dialog Display

Uses window layer positioned at bottom:
```c
move_win(7, 128);  // Position window
SHOW_WIN;          // Display dialog
```

## Build

```bash
make        # Build ROM
make run    # Build and run in SameBoy
make clean  # Remove build artifacts
```
