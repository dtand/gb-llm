# Fishing Minigame

A timing-based fishing minigame demonstrating reaction windows and state-based animation.

## Features

- **Timing Mechanics**: Press A at the right moment when a fish bites
- **Reaction Window**: Limited time to react when the exclamation appears
- **Random Wait Times**: Unpredictable timing keeps players alert
- **Water Animation**: Animated waves create atmosphere
- **Visual Feedback**: Bobber movement, bite indicator, catch/miss messages

## Controls

- **A Button**: Cast line / Catch fish when it bites

## Gameplay

1. Press A to cast your line into the water
2. Wait for the fish to bite (random timing)
3. When you see the **!** indicator, quickly press A
4. If you react in time, you catch the fish!
5. Too slow? The fish gets away

## Technical Highlights

### Timing System
- Random wait timer between MIN_WAIT (60 frames / 1 sec) and MAX_WAIT (240 frames / 4 sec)
- Bite window of 30 frames (~0.5 seconds) to react
- Creates tension without being unfair

### State Machine
```
TITLE → IDLE → CAST → WAITING → BITE → CATCH/MISS → IDLE
                                  ↓
                              (timeout)
```

### Animation Techniques
- Water tiles alternate between two frames for wave effect
- Bobber bobs up and down while waiting
- Exclamation flashes to draw attention
- Cast animation shows bobber arc

### Background-Only Rendering
- All graphics use background tiles (no sprites)
- Demonstrates tile-based animation
- Efficient for simple minigames

## Code Patterns Demonstrated

1. **Reaction Timing**: Window-based input detection
2. **Random Delays**: Unpredictable wait times
3. **Frame Animation**: Alternating tile frames
4. **State Machine**: Clean game flow
5. **Message Display**: Dynamic text rendering
6. **Scene Composition**: Layered background elements

## Building

```bash
make clean && make
```

## File Structure

```
fishing/
├── Makefile
├── metadata.json
├── README.md
├── build/
│   └── fishing.gb
└── src/
    ├── main.c      # Entry point and game loop
    ├── game.h      # Game state and declarations
    ├── game.c      # Fishing game logic
    ├── sprites.h   # Tile definitions
    └── sprites.c   # Tile graphics data
```
