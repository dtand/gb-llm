# VRAM Timing Flicker

## Category
VRAM / Display Timing

## Description
Flickering or corruption appears in the top portion of the screen (approximately the first 1/6, or ~24 scanlines / 3 tile rows). Tiles appear to randomly show wrong values or disappear briefly.

## Symptoms
- Flickering isolated to top of screen
- Corruption gets worse with more tile writes
- Bottom of screen renders correctly

## Root Cause
Writing to VRAM (Video RAM) outside of the VBlank period. The GameBoy LCD controller only allows safe VRAM access during:
1. VBlank (~1.1ms after each frame)
2. HBlank (brief period after each scanline)

When code writes to VRAM while the LCD is actively drawing scanlines, the writes are ignored or corrupted. The top of the screen is affected because VBlank ends and LCD drawing begins from scanline 0.

```c
// BAD: By the time we render, VBlank is over
while(1) {
    wait_vbl_done();
    game_handle_input();  // Takes time
    game_update();        // Takes more time
    game_render();        // VRAM writes happen too late!
}
```

## Prevention

**1. Render immediately after VBlank**
```c
while(1) {
    wait_vbl_done();
    game_render();        // VRAM writes while still in VBlank
    game_handle_input();  // Non-VRAM operations after
    game_update();
}
```

**2. Minimize tile writes per frame**
- Only update tiles that actually changed
- Use dirty flags to track what needs redrawing
- Consider double-buffering for complex scenes

**3. Use shadow buffers**
- Prepare tile data in RAM during the frame
- Copy to VRAM in one fast burst during VBlank

## Related Samples
- `puzzle` - Encountered and fixed this issue

## Hardware Reference
- VBlank duration: ~1.1ms (4560 cycles)
- Safe VRAM writes: During VBlank or when LCD disabled
- LCD draws scanlines 0-143 from top to bottom
