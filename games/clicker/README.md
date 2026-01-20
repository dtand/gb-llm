# Clicker

> Simple click counter that saves high score to battery-backed SRAM.

## Prompt

The exact prompt that should generate this game:

```
Create a simple clicker game where pressing A increases a counter. Save the highest count to battery-backed SRAM so it persists when the Game Boy is turned off. Display current count and high score.
```

## How to Play

| Control | Action |
|---------|--------|
| A Button | Increment counter |
| B Button | Reset current counter |
| START | Save high score |
| SELECT | Clear saved data |

## Game Rules

- Press A to increase count
- High score saved automatically when exceeded
- Press START to manually save
- SELECT clears saved data

## Technical Notes

### Save System (SRAM)
- Uses cartridge SRAM at 0xA000-0xBFFF
- Must enable SRAM with MBC register write
- Uses magic number to validate save data
- SRAM persists with battery backup

### Memory Layout
- 0xA000: Magic number (0x42) - validates save
- 0xA001-0xA002: High score (16-bit)

### Sprites Used
- Displays score using background tiles
- **Sprites: 0 (uses background only)**

## Build

```bash
make        # Build ROM
make run    # Build and launch in SameBoy
make clean  # Remove build artifacts
```

## Files

| File | Purpose |
|------|---------|
| `main.c` | Entry point, game loop |
| `game.h` | Save data structure, SRAM addresses |
| `game.c` | Counter logic, SRAM read/write |
| `sprites.h` | Number tile definitions |
| `sprites.c` | Number display tiles |
