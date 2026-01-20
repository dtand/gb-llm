# GameBoy Hardware Specifications

> Reference document for GB hardware constraints that inform code generation.

## CPU

| Property | Value |
|----------|-------|
| Processor | Sharp LR35902 (Z80-like) |
| Clock Speed | 4.19 MHz (DMG) |
| Instruction Set | Modified Z80 |

**Implications for Generation:**
- No floating point - use fixed-point math
- Limited registers - minimize complex expressions
- Slow division - use bit shifts where possible

## Memory Map

| Range | Size | Purpose |
|-------|------|---------|
| 0x0000-0x3FFF | 16KB | ROM Bank 0 (fixed) |
| 0x4000-0x7FFF | 16KB | ROM Bank 1-N (switchable) |
| 0x8000-0x9FFF | 8KB | Video RAM |
| 0xA000-0xBFFF | 8KB | External RAM (cartridge) |
| 0xC000-0xDFFF | 8KB | Work RAM |
| 0xFE00-0xFE9F | 160B | OAM (Sprite attributes) |
| 0xFF00-0xFF7F | 128B | I/O Registers |
| 0xFF80-0xFFFE | 127B | High RAM (HRAM) |

**Implications for Generation:**
- 8KB work RAM limits data structures
- Use ROM for constant data (lookup tables)
- HRAM is fastest - use for critical variables

## Display

| Property | Value |
|----------|-------|
| Resolution | 160 × 144 pixels |
| Tile Size | 8 × 8 pixels |
| Tiles on Screen | 20 × 18 tiles |
| Colors | 4 shades of green/gray |
| Background Layers | 1 background + 1 window |

### Sprite Limits

| Property | Value |
|----------|-------|
| Max Sprites | 40 total in OAM |
| Sprites per Scanline | 10 maximum |
| Sprite Sizes | 8×8 or 8×16 pixels |
| Sprite Colors | 3 + transparent |
| Sprite Palettes | 2 (OBP0, OBP1) |

**Implications for Generation:**
- Plan sprite usage carefully (max 10 per line!)
- Use background tiles for static elements
- Combine sprites for larger objects
- Consider flickering for >10 sprites on a line

### Tile Data

| Property | Value |
|----------|-------|
| Max Tiles | 384 tiles (256 BG + 128 shared) |
| Bytes per Tile | 16 bytes (2 bits per pixel) |
| Tile Maps | 32 × 32 tiles (only 20×18 visible) |

**Implications for Generation:**
- Reuse tiles where possible
- Design sprites with tile constraints in mind
- Use tile flipping to save tile slots

## Palettes

### Background Palette (BGP)
```
Bits 7-6: Color 3 (darkest)
Bits 5-4: Color 2
Bits 3-2: Color 1
Bits 1-0: Color 0 (lightest/transparent for window)
```

### Sprite Palettes (OBP0, OBP1)
```
Same as BGP, but color 0 is always transparent
```

**Color Values:**
| Value | DMG Appearance |
|-------|---------------|
| 0 | White/Lightest |
| 1 | Light Gray |
| 2 | Dark Gray |
| 3 | Black/Darkest |

## Input

### Joypad Register (0xFF00)

| Button | Bit |
|--------|-----|
| Right / A | 0 |
| Left / B | 1 |
| Up / Select | 2 |
| Down / Start | 3 |
| D-Pad Select | 4 |
| Button Select | 5 |

**Buttons Available:**
- D-Pad: Up, Down, Left, Right
- Action: A, B
- System: Start, Select

**Implications for Generation:**
- Only 8 buttons total - design controls accordingly
- No analog input - discrete movement only
- Consider button combinations sparingly (hard to press)

## Sound

### Channels

| Channel | Type | Use Case |
|---------|------|----------|
| 1 | Square wave + sweep | Melody, effects |
| 2 | Square wave | Harmony, effects |
| 3 | Wave (custom) | Bass, samples |
| 4 | Noise | Drums, explosions |

**Implications for Generation:**
- 4 channels means careful sound design
- Consider which sounds are essential
- Music competes with sound effects

## Timing

| Event | Duration |
|-------|----------|
| Frame | 16.74 ms (~59.7 FPS) |
| V-Blank | 1.1 ms (lines 144-153) |
| H-Blank | 51.2 μs per line |
| Mode 3 (Drawing) | Variable |

**Implications for Generation:**
- Update game logic during V-Blank
- Heavy computation may cause slowdown
- Target 60 FPS but handle slowdown gracefully

## ROM Sizes

| Size | Banks | Common Use |
|------|-------|------------|
| 32KB | 2 | Simple games (Tetris) |
| 64KB | 4 | Standard games |
| 128KB | 8 | Medium games |
| 256KB | 16 | Large games |
| 512KB | 32 | RPGs, complex games |
| 1MB+ | 64+ | Very large games |

**Implications for Generation:**
- Start with 32KB target for simple games
- Plan ROM banking for larger games
- Keep code in Bank 0, data can be banked

## GBDK-2020 Specifics

### Data Types

| Type | Size | Range |
|------|------|-------|
| `UINT8` | 1 byte | 0 to 255 |
| `INT8` | 1 byte | -128 to 127 |
| `UINT16` | 2 bytes | 0 to 65535 |
| `INT16` | 2 bytes | -32768 to 32767 |
| `UINT32` | 4 bytes | 0 to 4294967295 |

**Best Practices:**
- Prefer `UINT8` when possible (fastest)
- Avoid 32-bit math (very slow)
- Use `const` for ROM data

### Fixed Point Math

For positions/velocities requiring sub-pixel precision:

```c
// 8.8 fixed point (8 bits integer, 8 bits fraction)
typedef INT16 fixed;

#define FIXED_SHIFT 8
#define INT_TO_FIXED(x) ((x) << FIXED_SHIFT)
#define FIXED_TO_INT(x) ((x) >> FIXED_SHIFT)
#define FIXED_MUL(a, b) (((a) * (b)) >> FIXED_SHIFT)
```

### Memory Sections

```c
// ROM (constant data)
const UINT8 sprite_data[] = { ... };

// RAM (variables)
UINT8 player_x;

// HRAM (fast access)
__at(0xFF80) UINT8 fast_var;
```

## Constraints Summary for Code Generation

### DO:
- Use 8-bit integers where possible
- Keep sprite count under control
- Use lookup tables instead of computation
- Update sprites during V-Blank
- Reuse tiles and sprites
- Use bit operations for math

### DON'T:
- Use floating point numbers
- Exceed 10 sprites per scanline
- Perform heavy computation during draw
- Waste tile slots with unique tiles
- Use 32-bit math unnecessarily
- Ignore memory limits

## Quick Reference Card

```
Screen:     160×144 pixels, 20×18 tiles
Sprites:    40 max, 10 per line, 8×8 or 8×16
Colors:     4 shades per palette
RAM:        8KB work + 127B fast (HRAM)
ROM:        32KB minimum, banked for more
Buttons:    D-pad + A/B + Start/Select
Frame:      ~60 FPS (16.74ms per frame)
Sound:      4 channels (2 square, 1 wave, 1 noise)
```
