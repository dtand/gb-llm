# Zero Physics Constants

## Category
Physics / Game Balance

## Description
Player can fly infinitely, objects don't fall, or movement breaks because a physics constant is set to zero when it should have a non-zero value.

## Symptoms
- Infinite jump (player floats while holding button)
- Objects frozen in air
- No gravity during certain states
- Movement works initially then breaks

## Root Cause
Physics systems often have conditional gravity or reduced values for certain states. Setting these to zero breaks the simulation.

```c
// BAD: Zero gravity while holding jump = infinite flight
#define GRAVITY_NORMAL    1
#define GRAVITY_JUMP_HOLD 0  // Player holds A to fly forever!

void update_physics(void) {
    if (holding_jump && velocity_y < 0) {
        velocity_y += GRAVITY_JUMP_HOLD;  // Adds nothing!
    } else {
        velocity_y += GRAVITY_NORMAL;
    }
}
```

## Prevention

**1. Never use zero for physics values**
```c
// GOOD: Reduced gravity, but never zero
#define GRAVITY_NORMAL    2
#define GRAVITY_JUMP_HOLD 1  // Slower fall, but still falls

// Or apply every other frame:
if (holding_jump && (frame_count & 1)) {
    velocity_y += GRAVITY_NORMAL;  // Half gravity via timing
}
```

**2. Add minimum value assertions**
```c
#if GRAVITY_JUMP_HOLD == 0
#error "GRAVITY_JUMP_HOLD must be non-zero"
#endif
```

**3. Use frame-skipping instead of zero constants**
```c
// Apply gravity every N frames instead of using zero
#define GRAVITY_SKIP_FRAMES 2

void update_physics(void) {
    if (holding_jump) {
        if ((frame_count % GRAVITY_SKIP_FRAMES) == 0) {
            velocity_y += GRAVITY;
        }
    } else {
        velocity_y += GRAVITY;
    }
}
```

**4. Document physics state machine**
```c
// Jump states:
// - RISING (vy < 0, holding A): reduced gravity (1/2)
// - RISING (vy < 0, released A): full gravity  
// - FALLING (vy >= 0): full gravity + capped terminal velocity
// NEVER zero gravity in any state!
```

## Common Physics Values

| Constant | Bad Value | Good Value | Notes |
|----------|-----------|------------|-------|
| GRAVITY | 0 | 1-2 | Per-frame downward acceleration |
| GRAVITY_REDUCED | 0 | 1 or frame-skip | For variable jump |
| JUMP_VELOCITY | 0 | -4 to -8 | Initial upward velocity |
| TERMINAL_VELOCITY | 0 or 255 | 3-6 | Max fall speed |
| FRICTION | 0 | 1 | Gradual slowdown |

## Related Samples
- `platformer` - Infinite flight when JUMP_HOLD_GRAVITY was 0

## Notes
Zero is especially dangerous for:
- Gravity (causes floating)
- Friction (causes infinite sliding)
- Cooldowns (causes instant repeat)
- Damage (causes invincibility)
