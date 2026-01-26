# Racing Game

A top-down racing game demonstrating **vertical scrolling**, **speed mechanics**, and **lap counting**.

## Features Demonstrated

- **Vertical Scrolling**: Track scrolls based on player speed
- **Speed Control**: Acceleration and braking mechanics
- **Lap System**: 3 laps with finish line detection
- **Obstacle Avoidance**: AI cars to dodge
- **Metasprites**: 2x2 tile car sprites
- **HUD**: Lap counter, timer, speed display

## Controls

| Button | Action |
|--------|--------|
| D-Pad L/R | Steer left/right |
| A | Accelerate |
| B | Brake |
| START | Restart after finish |

## Gameplay

1. Race starts with 3-2-1 countdown
2. Hold A to accelerate, release to coast
3. Press B to brake quickly
4. Steer to avoid obstacle cars
5. Cross finish line 3 times to complete
6. Best time displayed at finish

## Technical Notes

### Speed System

```c
#define SPEED_MIN   0
#define SPEED_MAX   8
#define ACCEL_RATE  1
#define BRAKE_RATE  2

// Acceleration when A held
if (keys & J_A) {
    if (game.speed < SPEED_MAX) {
        game.speed += ACCEL_RATE;
    }
} else {
    // Natural deceleration
    if (game.speed > 0) game.speed--;
}
```

### Scroll Rate

Track scroll speed is directly tied to player speed:
```c
game.scroll_pos += game.speed;
SCY_REG = (scroll_tile * 8) + scroll_fine;
```

### Lap Detection

Finish line is at a fixed row in the repeating track:
```c
#define FINISH_LINE_ROW 4
#define TRACK_ROWS      32

if ((game.distance % TRACK_ROWS) == FINISH_LINE_ROW) {
    if (!game.crossed_line) {
        game.crossed_line = 1;
        game.lap++;
    }
}
```

### Obstacle Movement

Obstacles move relative to player speed:
```c
rel_speed = game.speed - 2;  // Base obstacle speed is 2
if (rel_speed < 1) rel_speed = 1;
obstacle.y += rel_speed;
```

### Track Layout

```
Column:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19
Tile:    G  G  G  B  R  R  R  R  R  C  R  R  R  R  R  B  G  G  G  G

G = Grass, B = Barrier, R = Road, C = Center line
```

### Collision Detection

Simple AABB between player and obstacles:
```c
dx = abs(player_x - obstacle_x);
dy = abs(player_y - obstacle_y);
if (dx < 14 && dy < 14) {
    // Collision - slow down
    game.speed = game.speed / 2;
}
```

## Build

```bash
make        # Build ROM
make run    # Build and run in SameBoy
make clean  # Remove build artifacts
```

## Patterns for LLM Generation

This sample demonstrates patterns useful for:
- Any scrolling game with variable speed
- Racing or driving games
- Lap-based or checkpoint systems
- Timer and HUD displays
- Countdown sequences
- Obstacle avoidance mechanics
