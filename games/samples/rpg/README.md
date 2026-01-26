# RPG Battle Demo

A turn-based RPG battle system demonstrating **menu navigation**, **state machines**, and **stat management**.

## Features Demonstrated

- **Menu System**: 2x2 grid menu with D-pad navigation
- **State Machine**: Turn-based flow (Menu → Player → Enemy → Menu)
- **Stat Bars**: Visual HP and MP bars using tile-based rendering
- **Combat Calculation**: Attack, defense, and random variance
- **Metasprites**: 16x16 hero sprite using 4 hardware sprites

## Controls

| Button | Action |
|--------|--------|
| D-Pad | Navigate menu (2x2 grid) |
| A | Select action |
| START | Restart after victory/defeat |

## Gameplay

1. **ATTACK**: Physical attack dealing damage based on ATK vs DEF
2. **MAGIC**: Powerful spell (15 damage) costing 5 MP
3. **DEFEND**: Halve incoming damage for one turn
4. **FLEE**: Attempt to escape (chance increases with each try)

## Technical Notes

### State Machine

The battle uses a simple state machine:

```c
#define STATE_MENU          0   // Player selecting action
#define STATE_PLAYER_TURN   1   // Player action executing
#define STATE_ENEMY_TURN    2   // Enemy action executing
#define STATE_VICTORY       4   // Player won
#define STATE_DEFEAT        5   // Player lost
#define STATE_FLEE          6   // Player escaped
```

### Combat Stats

```c
typedef struct {
    int8_t hp, max_hp;
    int8_t mp, max_mp;
    uint8_t attack;
    uint8_t defense;
    uint8_t defending;
} Combatant;
```

### Damage Formula

```c
damage = attack - (defense / 2);
if (defending) damage /= 2;
damage += random(-2, +2);
if (damage < 1) damage = 1;
```

### Menu Layout

```
┌────────┬──────────┐
│>ATTACK │ DEFEND   │
│ MAGIC  │ FLEE     │
└────────┴──────────┘
```

Navigation wraps with D-pad:
- UP/DOWN: Move within column
- LEFT/RIGHT: Move between columns

### Visual Elements

- **Hero**: 16x16 metasprite (4 sprites) positioned on left
- **Monster**: 32x32 graphic using background tiles
- **HP Bar**: 6 tiles wide, filled/empty segments
- **MP Bar**: 4 tiles wide, different pattern for MP

## Build

```bash
make        # Build ROM
make run    # Build and run in SameBoy
make clean  # Remove build artifacts
```

## Patterns for LLM Generation

This sample demonstrates patterns useful for:
- Any game requiring menu systems
- Turn-based games (card games, strategy)
- Games with character stats
- UI with multiple interactable boxes
