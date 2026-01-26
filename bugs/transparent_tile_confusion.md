# Transparent Tile Confusion

## Category
Graphics / Tile Data

## Description
UI elements, backgrounds, or dialog boxes appear as "holes" in the display instead of solid colors. The area shows as empty/transparent when it should be filled.

## Symptoms
- Dialog box appears as cutout showing layer beneath
- Background areas are see-through
- UI elements have holes in them
- Window layer shows background through it

## Root Cause
Using a tile with all-zero data (0x00), which is transparent, when a solid tile is needed. Often happens when reusing the "empty" tile for areas that should be filled.

```c
// BAD: Floor tile is all zeros (transparent)
const uint8_t floor_tile[] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

// Then used for dialog background:
void show_dialog(void) {
    for (x = 0; x < 20; x++) {
        set_win_tile_xy(x, 1, BG_FLOOR);  // Shows as transparent!
    }
}
```

## GameBoy Tile Format
Each tile is 8x8 pixels, 2 bits per pixel (4 colors).
- 16 bytes per tile (2 bytes per row)
- Byte pairs: low-bits, high-bits
- Color 0 (both bits = 0) is typically transparent for sprites

```c
// All zeros = color 0 everywhere = transparent
0x00, 0x00  // Row: 00000000, 00000000 → all color 0

// All ones in first byte = color 1 (light gray by default)
0xFF, 0x00  // Row: 11111111, 00000000 → all color 1

// All ones in both = color 3 (black by default)
0xFF, 0xFF  // Row: 11111111, 11111111 → all color 3
```

## Prevention

**1. Create dedicated solid tiles for UI**
```c
// Solid white/light tile for dialog background
const uint8_t dialog_bg_tile[] = {
    0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00,
    0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00
};
// All pixels = color 1 (light gray, or white with custom palette)
```

**2. Don't reuse game tiles for UI**
```c
// Separate tile indices for game vs UI
#define BG_FLOOR        0   // Game floor (may be transparent)
#define BG_WALL         1   // Game wall

#define UI_DIALOG_BG    10  // Dedicated solid UI background
#define UI_DIALOG_FRAME 11  // Dedicated UI border
```

**3. Test tiles in isolation**
```c
// Debug: fill screen with single tile to see its appearance
for (y = 0; y < 18; y++) {
    for (x = 0; x < 20; x++) {
        set_bkg_tile_xy(x, y, TILE_TO_TEST);
    }
}
```

## Common Tile Patterns

| Purpose | Byte Pattern | Result |
|---------|--------------|--------|
| Transparent | 0x00, 0x00 | Color 0 (transparent) |
| Solid light | 0xFF, 0x00 | Color 1 (light) |
| Solid dark | 0x00, 0xFF | Color 2 (dark) |
| Solid black | 0xFF, 0xFF | Color 3 (black) |
| Checkerboard | 0xAA, 0x55 | Dithered pattern |

## Related Samples
- `adventure` - Dialog box was a "hole" until solid dialog tile was added

## Notes
The Window layer sits on top of the Background layer. If Window tiles are transparent, the Background shows through - which is sometimes desired (for HUD with transparent parts) but not for solid dialog boxes.
