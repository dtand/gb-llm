# Screen Size Mismatch

## Category
Hardware Constraints / Data Structure Design

## Description
Game elements fall through the bottom of the screen, appear off-screen, or collision detection fails at screen edges because data structures use wrong dimensions.

## Symptoms
- Objects pass through what should be solid boundaries
- Elements visible beyond screen edges in debug
- Collision works in middle of screen but not edges
- Array index out of bounds crashes

## Root Cause
Hardcoding dimensions that don't match the GameBoy's actual screen size.

```c
// BAD: Screen is NOT 20 tiles tall!
#define GRID_HEIGHT 20

// GameBoy screen is 160x144 pixels = 20x18 tiles
// - Width: 160 pixels ÷ 8 = 20 tiles ✓
// - Height: 144 pixels ÷ 8 = 18 tiles ✗ (not 20!)
```

Common mistakes:
- Using 20x20 (square assumption)
- Using 256x256 (full tilemap size, not visible area)
- Mixing pixel and tile coordinates

## Prevention

**1. Use hardware constants, not magic numbers**
```c
// Correct GameBoy screen dimensions
#define SCREEN_WIDTH_PX     160
#define SCREEN_HEIGHT_PX    144
#define SCREEN_WIDTH_TILES  (SCREEN_WIDTH_PX / 8)   // 20
#define SCREEN_HEIGHT_TILES (SCREEN_HEIGHT_PX / 8)  // 18
#define TILE_SIZE           8
```

**2. Validate at compile time**
```c
// Static assert to catch mistakes
#if GRID_HEIGHT > 18
#error "Grid height exceeds visible screen area"
#endif
```

**3. Document the distinction between tilemap and screen**
```c
// Full background tilemap: 32x32 tiles (256x256 pixels)
// Visible screen window: 20x18 tiles (160x144 pixels)
// Only 20x18 is visible without scrolling!
```

## GameBoy Screen Reference

| Measurement | Pixels | Tiles (8x8) |
|-------------|--------|-------------|
| Width | 160 | 20 |
| Height | 144 | 18 |
| Background map | 256x256 | 32x32 |
| Window layer | 160x144 | 20x18 |
| Sprite area | 160x144 | 20x18 |

## Related Samples
- `puzzle` - Grid was 20 rows but screen only shows 18

## Notes
The background tilemap is 32x32 tiles, but the visible "viewport" is only 20x18. This is important for:
- Scrolling games (can scroll within the larger tilemap)
- Fixed-screen games (must fit in 20x18)
