# Melody

> Music demo with background music using Game Boy sound channels.

## Prompt

The exact prompt that should generate this game:

```
Create a simple music player demo that plays a melody using the Game Boy's sound channels. Display a visual indicator that pulses with the music. Use D-pad to change tempo.
```

## How to Play

| Control | Action |
|---------|--------|
| D-Pad Up/Down | Change tempo |
| A Button | Play/pause music |
| START | Reset to default |

## Technical Notes

### Sound System
- Uses Channel 1 (square wave with sweep)
- Note frequency set via NR13/NR14 registers
- Volume envelope via NR12
- Simple sequencer plays note array

### Sound Registers Used
- NR10: Sweep (channel 1)
- NR11: Wave duty/length
- NR12: Volume envelope
- NR13: Frequency low
- NR14: Frequency high + trigger
- NR50: Master volume
- NR51: Sound panning
- NR52: Sound on/off

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
| `game.h` | Music state, note definitions |
| `game.c` | Sequencer logic, sound playback |
| `sprites.h` | Visual indicator sprites |
| `sprites.c` | Sprite tile data |
