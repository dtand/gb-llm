# Parallax Scroller

A landscape demo demonstrating **parallax scrolling** with multiple background layers moving at different speeds to create depth.

## Features Demonstrated

- **Parallax Scrolling**: Multiple layers scroll at different speeds
- **LYC Interrupt**: Scanline-based interrupt to change scroll mid-frame
- **Depth Illusion**: Far mountains scroll slowly, near ground scrolls fast
- **Scene Composition**: Layered landscape with sky, mountains, hills, ground

## Controls

| Button | Action |
|--------|--------|
| D-Pad Left/Right | Scroll the scene |
| A (hold) | Scroll faster |

## How It Works

The GameBoy only has one background layer, but we can create a parallax effect by changing the SCX (scroll X) register at different scanlines during the frame.

### Scanline Regions

| Scanlines | Layer | Scroll Speed |
|-----------|-------|--------------|
| 0-31 | Sky | No scroll (static) |
| 32-63 | Mountains | 1/4 speed (slow) |
| 64-95 | Hills | 1/2 speed (medium) |
| 96-143 | Ground | Full speed (fast) |

### LYC Interrupt

The LY register counts the current scanline (0-153). We can set LYC (LY Compare) to trigger an interrupt at a specific scanline:

```c
// Trigger interrupt at scanline 32
LYC_REG = 32;

// In the interrupt handler:
void lcd_isr(void) {
    switch (LY_REG) {
        case 32: SCX_REG = scroll_mountain; LYC_REG = 64; break;
        case 64: SCX_REG = scroll_hills; LYC_REG = 96; break;
        case 96: SCX_REG = scroll_ground; LYC_REG = 32; break;
    }
}
```

## Technical Notes

### STAT Register
The STAT register (0xFF41) controls LCD interrupts:
- Bit 6: LYC=LY interrupt enable
- Bits 3-5: Other mode interrupts

### Timing Considerations
Scroll register changes must happen during HBlank (between scanlines) to avoid visual tearing. The LYC interrupt fires at the start of the scanline, giving time to update SCX before pixels are drawn.

## Build

```bash
make        # Build ROM
make run    # Build and run in SameBoy
make clean  # Remove build artifacts
```
