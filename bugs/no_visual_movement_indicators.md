# No Visual Movement Indicators

## Category
Visual Design / Scrolling

## Description
Scrolling layers or moving backgrounds appear completely static even though the scroll registers are being updated correctly. The layer is scrolling, but it doesn't look like it.

## Symptoms
- Parallax layer looks frozen
- Background doesn't appear to move
- Scrolling code runs but no visible effect
- Movement only visible at edges where tiles wrap

## Root Cause
The tiles in the scrolling layer are uniform or repetitive, providing no visual reference points to perceive movement. A solid color or repeating pattern looks identical at any scroll position.

```c
// Scrolling IS happening:
void update(void) {
    scroll_x++;
    SCX_REG = scroll_x;  // Register updates correctly
}

// But the tiles are all the same:
const uint8_t sky_tile[] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};  // Uniform = no visible movement!
```

## Prevention

**1. Add visual markers to moving layers**
```c
// Place distinctive tiles at intervals
void draw_ground_layer(void) {
    for (x = 0; x < 32; x++) {
        if (x % 8 == 0) {
            set_bkg_tile_xy(x, GROUND_ROW, TILE_TREE);  // Landmark
        } else {
            set_bkg_tile_xy(x, GROUND_ROW, TILE_GRASS);
        }
    }
}
```

**2. Use tiles with internal detail**
```c
// Ground tile with texture instead of solid color
const uint8_t ground_tile[] = {
    0xFF, 0xFF, 0x81, 0xFF, 0xBD, 0xFF, 0xA5, 0xFF,
    0xA5, 0xFF, 0xBD, 0xFF, 0x81, 0xFF, 0xFF, 0xFF
};  // Has visible pattern that moves with scroll
```

**3. Vary tile placement**
```c
// Don't use the same tile everywhere
void draw_sky(void) {
    for (x = 0; x < 32; x++) {
        // Mix in cloud tiles randomly
        uint8_t tile = (pseudo_random(x) % 4 == 0) ? TILE_CLOUD : TILE_SKY;
        set_bkg_tile_xy(x, y, tile);
    }
}
```

**4. Use different scroll speeds for layers**
```c
// Parallax layers at different speeds prove movement
far_bg_scroll   += 1;  // Slow
mid_bg_scroll   += 2;  // Medium  
near_bg_scroll  += 4;  // Fast (relative motion is visible)
```

## Visual Reference Guidelines

| Layer | Good Markers | Bad (Invisible) |
|-------|--------------|-----------------|
| Sky | Clouds, stars, sun | Solid color |
| Far mountains | Peaks, varied heights | Flat line |
| Mid ground | Trees, rocks, buildings | Solid fill |
| Near ground | Grass tufts, flowers | Uniform tiles |

## Related Samples
- `parallax` - Ground layer looked static until trees/rocks were added

## Notes
This is purely a visual design issue, not a code bug. The scrolling works correctly - it's just imperceptible without reference points. Always test scrolling with placeholder "landmark" tiles during development.
