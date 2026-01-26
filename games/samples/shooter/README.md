# Space Shooter

A vertical scrolling space shooter demonstrating **vertical scrolling**, **metasprites**, and the **window layer** for HUD display.

## Features Demonstrated

- **Vertical Scrolling**: Background stars scroll downward using the SCY register
- **Metasprites**: Player ship composed of 4 sprites (16x16 pixels)
- **Window Layer**: Score and lives displayed in a static HUD at the top
- **Entity Management**: Multiple bullets and enemies with pooling
- **Collision Detection**: AABB collision between bullets and enemies

## Controls

| Button | Action |
|--------|--------|
| D-Pad Left/Right | Move ship |
| A | Fire bullet |
| START | Restart (after game over) |

## Technical Notes

### Window Layer
The GameBoy window layer is a secondary background that can overlay the main background. It's positioned using WX and WY registers:
- `WX_REG`: X position (offset by 7, so WX=7 is left edge)
- `WY_REG`: Y position (WY=0 is top)

The window is ideal for HUDs because it doesn't scroll with the background.

### Metasprites
A metasprite combines multiple 8x8 hardware sprites into a larger visual sprite. For a 16x16 ship:
```
[0][1]   <- Sprites 0,1 at y
[2][3]   <- Sprites 2,3 at y+8
```

### Vertical Scrolling
Unlike horizontal scrolling (SCX), vertical scrolling (SCY) wraps at 256 pixels but the visible area is only 144 pixels tall, giving more offscreen space for seamless wrapping.

## Build

```bash
make        # Build ROM
make run    # Build and run in SameBoy
make clean  # Remove build artifacts
```
