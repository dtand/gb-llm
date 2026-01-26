# Insufficient Velocity Tuning

## Category
Game Balance / Physics Tuning

## Description
Movement values (jump height, speed, gravity) are technically correct but don't produce playable results. Player can't reach platforms, moves too slow/fast, or jumps feel wrong.

## Symptoms
- Player can't reach visible platforms
- Movement feels "floaty" or "heavy"
- Speed too slow for gameplay pacing
- Jumps too short or too high for level design

## Root Cause
Physics constants were chosen arbitrarily or mathematically without playtesting. The values work but don't match the level design or feel expectations.

```c
// Technically works, but JUMP_VELOCITY too weak for level design
#define GRAVITY         1
#define JUMP_VELOCITY  -4  // Only reaches ~8 pixels high
#define TERMINAL_VEL    4

// Level has platforms 24 pixels apart - impossible to reach!
```

## Prevention

**1. Calculate required values from level design**
```c
// Platform is 3 tiles (24 pixels) above ground
// Jump must reach at least 24 pixels
// 
// Physics: height = v² / (2 * g)
// With g=1: v² = 2 * 1 * 24 = 48, v = ~7
// 
#define JUMP_VELOCITY  -7  // Reaches ~24 pixels
#define GRAVITY         1
```

**2. Test incrementally with visible feedback**
```c
// Debug: show max jump height
static int16_t max_height = 0;
if (player_y < max_height) max_height = player_y;
// Display max_height to tune values
```

**3. Use reference values from similar games**
```c
// Common platformer ratios:
// - Jump height ≈ 2-4 tiles
// - Jump duration ≈ 0.5-1 second
// - Run speed ≈ 2-4 pixels/frame
// - Gravity ≈ 0.5-2 pixels/frame²
```

**4. Document the feel you're targeting**
```c
// Target feel: "Mario-like responsive jump"
// - Tap jump: ~1.5 tiles high
// - Hold jump: ~3 tiles high
// - Air control: full horizontal movement
// - Landing: immediate stop, no slide
```

## Common Value Ranges (8-bit, 60fps)

| Parameter | Too Low | Good Range | Too High |
|-----------|---------|------------|----------|
| JUMP_VELOCITY | -2 to -4 | -5 to -8 | -10+ |
| GRAVITY | 0 | 1-2 | 3+ |
| WALK_SPEED | 1 | 2-3 | 4+ |
| TERMINAL_VEL | 2 | 4-6 | 8+ |

## Tuning Process

1. Set gravity first (determines feel weight)
2. Set jump velocity to reach desired height
3. Adjust terminal velocity so falling isn't jarring
4. Fine-tune with actual level geometry
5. Playtest and iterate

## Related Samples
- `platformer` - Jump velocity -4 was too weak, increased to -6

## Notes
These values interact:
- Higher gravity needs higher jump velocity
- Faster movement needs larger collision margins
- All values must be re-tuned if one changes significantly
