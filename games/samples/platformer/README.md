# Platformer

A simple platformer demonstrating **platform collision**, **variable jump height**, and **gravity physics**.

## Features Demonstrated

- **Platform Collision**: Tile-based collision detection for landing on platforms
- **Variable Jump**: Hold A longer for higher jumps
- **Gravity**: Continuous downward acceleration with terminal velocity
- **Movement**: Smooth left/right movement with boundaries

## Controls

| Button | Action |
|--------|--------|
| D-Pad Left/Right | Move |
| A | Jump (hold for higher) |
| START | Restart |

## Gameplay

Navigate the player character across platforms. The level has:
- Ground floor at the bottom
- Several floating platforms at different heights
- Jump between platforms to explore

## Technical Notes

### Variable Jump Height

The variable jump is achieved by:
1. Initial jump gives upward velocity
2. While A is held AND velocity is upward, reduce gravity effect
3. When A is released, normal gravity applies immediately

```c
if (jumping && holding_a && velocity_y < 0) {
    // Reduced gravity while holding A and moving up
    velocity_y += GRAVITY / 2;
} else {
    velocity_y += GRAVITY;
}
```

### Platform Collision

Collision checks the tile at the player's feet:
1. Convert pixel position to tile coordinates
2. Check if tile at (x, y+height) is solid
3. If solid and falling, land on platform
4. If not solid, apply gravity

```c
uint8_t tile_x = player_x / 8;
uint8_t tile_y = (player_y + PLAYER_HEIGHT) / 8;
uint8_t tile = get_bkg_tile_xy(tile_x, tile_y);

if (tile == TILE_PLATFORM && velocity_y >= 0) {
    // Land on platform
    player_y = (tile_y * 8) - PLAYER_HEIGHT;
    velocity_y = 0;
    on_ground = 1;
}
```

### Tile Map Layout

The level is defined as a 20x18 tile map where:
- Empty tiles (0) = air
- Platform tiles (1) = solid ground/platforms

## Build

```bash
make        # Build ROM
make run    # Build and run in SameBoy
make clean  # Remove build artifacts
```
