# Erase-Then-Redraw Flicker

## Category
Rendering / Animation

## Description
Moving objects flicker or briefly disappear during movement. The object is visible, then invisible for one frame, then visible again at the new position.

## Symptoms
- Objects "blink" while moving
- Flicker happens every frame during movement
- More noticeable on faster-moving objects

## Root Cause
The rendering code erases the object at its old position, then draws it at the new position. For one frame, the tile shows the erased (empty) state before being redrawn.

```c
// BAD: Erase then redraw creates 1-frame gap
void render(void) {
    // Erase at old position
    set_bkg_tile_xy(old_x, old_y, TILE_EMPTY);  // Frame shows empty here!
    
    // Draw at new position
    set_bkg_tile_xy(new_x, new_y, TILE_OBJECT);
}
```

If old and new positions overlap (common for slow movement), tiles get erased then immediately redrawn - causing visible flicker.

## Prevention

**1. Diff-based updates - only change what's different**
```c
void render(void) {
    // Only erase tiles that won't be redrawn
    for each old_tile {
        if (!will_be_covered_by_new_position(old_tile)) {
            erase(old_tile);
        }
    }
    // Draw new position (some tiles may overwrite old)
    draw_object(new_x, new_y);
}
```

**2. Never erase tiles you're about to redraw**
```c
// Check if old tile position overlaps with new
if (old_x != new_x || old_y != new_y) {
    // Only erase if positions are different
    set_bkg_tile_xy(old_x, old_y, TILE_EMPTY);
}
set_bkg_tile_xy(new_x, new_y, TILE_OBJECT);
```

**3. Use sprites instead of background tiles**
Sprites can be moved without erasing - the hardware handles transparency.

## Related Samples
- `puzzle` - Falling blocks flickered until diff-based rendering was implemented

## Notes
This is especially problematic for:
- Tetris-style games with falling pieces
- Any tile-based animation on the background layer
- Objects that move slowly (1 tile at a time)
