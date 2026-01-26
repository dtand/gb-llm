# Memory Card Game

A classic card matching memory game demonstrating **grid selection**, **card state tracking**, and **match detection**.

## Features Demonstrated

- **Grid System**: 4x4 grid of cards (16 cards, 8 pairs)
- **Card States**: Face-down, face-up, and matched states
- **Cursor Navigation**: D-pad movement with visual cursor
- **Match Detection**: Compare flipped cards and handle matches
- **Shuffle Algorithm**: Fisher-Yates randomization

## Controls

| Button | Action |
|--------|--------|
| D-Pad | Move cursor |
| A | Flip selected card |
| START | Restart after victory |

## Gameplay

1. All 16 cards start face-down
2. Move cursor and press A to flip a card
3. Flip a second card to check for a match
4. Matching pairs stay revealed
5. Non-matching cards flip back after a delay
6. Win when all 8 pairs are matched

## Technical Notes

### Card State Machine

Each card has three possible states:
```c
#define CARD_FACE_DOWN  0   // Back showing
#define CARD_FACE_UP    1   // Symbol visible
#define CARD_MATCHED    2   // Pair found, removed
```

### Game Flow States

```c
#define STATE_SELECTING_FIRST   0   // Picking first card
#define STATE_SELECTING_SECOND  1   // Picking second card
#define STATE_SHOWING_CARDS     2   // Brief reveal delay
#define STATE_VICTORY           3   // All pairs matched
```

### Grid Layout

Cards are arranged in a 4x4 grid:
```
Position = cursor_y * 4 + cursor_x

[0 ][1 ][2 ][3 ]
[4 ][5 ][6 ][7 ]
[8 ][9 ][10][11]
[12][13][14][15]
```

### Shuffle Algorithm

Uses Fisher-Yates shuffle for fair randomization:
```c
for (i = 15; i > 0; i--) {
    j = rand() % (i + 1);
    swap(cards[i], cards[j]);
}
```

### Card Symbols

8 unique symbols for 8 pairs:
- ★ Star
- ♥ Heart
- ◆ Diamond
- ♣ Club
- ☽ Moon
- ☀ Sun
- ⚡ Bolt
- ☠ Skull

## Build

```bash
make        # Build ROM
make run    # Build and run in SameBoy
make clean  # Remove build artifacts
```

## Patterns for LLM Generation

This sample demonstrates patterns useful for:
- Any grid-based puzzle game
- Games with hidden/revealed states
- Turn-based selection games
- Matching or pairing mechanics
