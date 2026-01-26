# Slot Machine

A classic slot machine game demonstrating reel animation, payout calculation, and coin management.

## Features

- **Three Spinning Reels**: Each reel spins independently with staggered stopping
- **Five Symbols**: Cherry, Bell, Bar, Seven, Star - each with different payouts
- **Coin System**: Start with 100 coins, bet 10 per spin
- **Payout Table**: Three-of-a-kind wins big, pairs and single cherries also pay
- **Animated Spinning**: Reels cycle through symbols with timing-based animation

## Controls

- **A Button**: Spin the reels (costs 10 coins)
- **START**: Restart game after running out of coins

## Payout Table

| Combination | Payout |
|-------------|--------|
| 🍒🍒🍒 (Three Cherries) | 50 coins |
| 🔔🔔🔔 (Three Bells) | 100 coins |
| 📊📊📊 (Three Bars) | 200 coins |
| 7️⃣7️⃣7️⃣ (Three Sevens) | 500 coins |
| ⭐⭐⭐ (Three Stars) | 1000 coins |
| XX (Any pair in first two) | 5-100 coins |
| Any single Cherry | 2 coins |

## Technical Highlights

### Reel Animation
- Reels spin at fixed frame intervals
- Each reel has independent spin counter
- Staggered stopping creates classic slot feel
- Final symbol determined by RNG when stopping

### Payout System
- Three-of-a-kind pays 10x base symbol value
- Two-of-a-kind (first two reels) pays base value
- Any cherry on screen pays 2 coins
- Encourages continued play with small wins

### Symbol Rendering
- Each symbol is 2x2 tiles (16x16 pixels)
- Symbols stored as sequential tile sets
- Simple draw function updates all 4 tiles

### State Machine
```
TITLE → IDLE ←→ SPINNING → RESULT → IDLE
              ↓
           GAMEOVER → (START) → IDLE
```

## Code Patterns Demonstrated

1. **Reel Animation**: Timed symbol cycling with staggered stops
2. **Payout Calculation**: Multi-tier win detection
3. **Coin Management**: Currency tracking and betting
4. **Box Drawing**: UI frames using edge/corner tiles
5. **LCG Random**: Pseudo-random for fair results
6. **State Machine**: Clean game flow management

## Building

```bash
make clean && make
```

## File Structure

```
slots/
├── Makefile
├── metadata.json
├── README.md
├── build/
│   └── slots.gb
└── src/
    ├── main.c      # Entry point and game loop
    ├── game.h      # Game state and declarations
    ├── game.c      # Slot machine logic
    ├── sprites.h   # Symbol and tile definitions
    └── sprites.c   # Symbol graphics data
```
