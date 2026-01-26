# Simon Pattern Game

A classic pattern memory game demonstrating **sequence tracking**, **audio feedback**, and **timed input**.

## Features Demonstrated

- **Pattern Sequence**: Growing array of random directions
- **Audio Feedback**: Different tone for each button
- **Visual Feedback**: Buttons light up when pressed/shown
- **Timed Input**: Timeout if player waits too long
- **Score Tracking**: Rounds completed

## Controls

| Button | Action |
|--------|--------|
| D-Pad | Press matching direction |
| START | Start game / Restart |

## Gameplay

1. Press START to begin
2. Watch the pattern (buttons light up with sounds)
3. Repeat the pattern using D-pad
4. Each round adds one more step
5. Game over if wrong button or timeout
6. Max sequence is 32 steps (WIN!)

## Technical Notes

### Sound Generation

Each button has a unique frequency using Channel 1 (pulse wave):

```c
#define FREQ_UP     0x0500  // Higher pitch
#define FREQ_RIGHT  0x0580
#define FREQ_DOWN   0x0600
#define FREQ_LEFT   0x0680  // Lower pitch

void play_tone(uint8_t button) {
    NR52_REG = 0x80;    // Sound on
    NR50_REG = 0x77;    // Volume max
    NR51_REG = 0x11;    // Channel 1 output
    NR10_REG = 0x00;    // No sweep
    NR11_REG = 0x80;    // 50% duty
    NR12_REG = 0xF0;    // Volume 15
    NR13_REG = freq & 0xFF;
    NR14_REG = 0x80 | ((freq >> 8) & 0x07);
}
```

### State Machine

```c
#define STATE_TITLE         0   // Press START
#define STATE_SHOW_PATTERN  1   // Computer's turn
#define STATE_PLAYER_INPUT  2   // Player's turn
#define STATE_CORRECT       3   // Brief pause
#define STATE_GAME_OVER     4   // Wrong input
#define STATE_WIN           5   // Max sequence reached
```

### Pattern Storage

```c
uint8_t sequence[MAX_SEQUENCE];  // Array of button indices (0-3)
uint8_t sequence_length;         // Current length
uint8_t current_step;            // Position during show/input

void add_to_sequence(void) {
    sequence[sequence_length] = rand() & 0x03;
    sequence_length++;
}
```

### Input Detection

Uses edge detection to catch newly pressed buttons:

```c
uint8_t keys = joypad();
uint8_t pressed = keys & ~last_keys;  // Rising edge

if (pressed & J_UP) input_button = BTN_UP;
// etc.

last_keys = keys;
```

### Timing Constants

```c
#define FLASH_FRAMES    20   // Button lit duration
#define PAUSE_FRAMES    10   // Gap between flashes
#define INPUT_TIMEOUT   120  // 2 seconds to respond
```

## Build

```bash
make        # Build ROM
make run    # Build and run in SameBoy
make clean  # Remove build artifacts
```

## Patterns for LLM Generation

This sample demonstrates patterns useful for:
- Any sequence/pattern memory game
- Games requiring audio feedback
- Timed input challenges
- Turn-based (show then input) gameplay
- State machines with multiple phases
