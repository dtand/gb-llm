# Missing Collision Direction

## Category
Physics / Collision Detection

## Description
Collision detection only works in one direction - typically ground collision exists but ceiling collision doesn't, or horizontal but not vertical.

## Symptoms
- Player can jump through platforms from below
- Enemies pass through walls from certain directions
- Objects stick when hitting obstacles from one side
- Collision works going right but not left

## Root Cause
Implementing collision for the most obvious case (landing on ground) but forgetting the reverse case (hitting ceiling) or perpendicular directions.

```c
// BAD: Only checks ground, not ceiling
void update_player(void) {
    velocity_y += GRAVITY;
    
    if (check_ground_collision()) {
        velocity_y = 0;
        on_ground = 1;
    }
    // Missing: What happens when jumping into ceiling?
    // Player phases through platforms from below!
}
```

## Prevention

**1. Check all four directions separately**
```c
void update_player(void) {
    // Apply gravity
    velocity_y += GRAVITY;
    
    // Vertical collision
    if (velocity_y > 0) {
        // Moving down - check ground
        if (check_ground()) {
            velocity_y = 0;
            on_ground = 1;
        }
    } else if (velocity_y < 0) {
        // Moving up - check ceiling
        if (check_ceiling()) {
            velocity_y = 0;  // Stop upward movement
        }
    }
    
    // Horizontal collision
    if (velocity_x > 0) {
        if (check_right_wall()) velocity_x = 0;
    } else if (velocity_x < 0) {
        if (check_left_wall()) velocity_x = 0;
    }
}
```

**2. Use symmetric collision functions**
```c
// Check collision in direction of movement
uint8_t check_tile_collision(int8_t dx, int8_t dy) {
    int16_t check_x = player_x + dx;
    int16_t check_y = player_y + dy;
    return is_solid_tile(check_x / 8, check_y / 8);
}

// Usage:
if (velocity_y < 0 && check_tile_collision(0, -1)) { /* ceiling */ }
if (velocity_y > 0 && check_tile_collision(0, 8))  { /* ground */ }
if (velocity_x < 0 && check_tile_collision(-1, 0)) { /* left wall */ }
if (velocity_x > 0 && check_tile_collision(8, 0))  { /* right wall */ }
```

**3. Collision response checklist**
```c
// For every collision check, answer:
// - Ground (moving down)?     → Stop fall, set on_ground
// - Ceiling (moving up)?      → Stop jump, maybe bonk sound
// - Left wall (moving left)?  → Stop horizontal movement
// - Right wall (moving right)? → Stop horizontal movement
// - Corner cases?             → Prioritize vertical or horizontal
```

## Collision Direction Matrix

| Movement | Check Location | Response |
|----------|---------------|----------|
| Down (vy > 0) | Below feet | Stop, set grounded |
| Up (vy < 0) | Above head | Stop, reverse or zero velocity |
| Left (vx < 0) | Left edge | Stop horizontal |
| Right (vx > 0) | Right edge | Stop horizontal |

## Related Samples
- `platformer` - Player could jump through platforms until ceiling check added

## Notes
Order matters! Typically check vertical collision first, then horizontal, to avoid corner-case glitches. Some games check all four and resolve the smallest penetration first.
