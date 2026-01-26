# Stale State After Spawn

## Category
State Management / Entity Lifecycle

## Description
When a new entity spawns (new piece, new enemy, respawned player), rendering glitches occur because the "previous state" tracking variables still contain data from the old/dead entity.

## Symptoms
- Brief visual glitch when new entity appears
- Wrong tiles get erased on first frame
- Ghost of previous entity appears momentarily
- Corruption at spawn location

## Root Cause
Many rendering systems track "previous position" to know what to erase. When an entity is replaced, the previous position data isn't reset, causing the renderer to erase tiles based on the OLD entity's shape/position.

```c
// Tracking state for diff-based rendering
typedef struct {
    int8_t prev_x, prev_y;
    uint8_t prev_type, prev_rotation;
} RenderState;

void spawn_new_piece(void) {
    current.type = next_type;
    current.x = SPAWN_X;
    current.y = SPAWN_Y;
    // BUG: prev_* still has OLD piece data!
    // Next render will erase tiles at wrong positions
}
```

## Prevention

**1. Sync previous state immediately on spawn**
```c
void spawn_new_piece(void) {
    current.type = next_type;
    current.x = SPAWN_X;
    current.y = SPAWN_Y;
    current.rotation = 0;
    
    // Immediately sync prev state to current
    prev_x = current.x;
    prev_y = current.y;
    prev_type = current.type;
    prev_rotation = current.rotation;
}
```

**2. Use a "first frame" flag**
```c
void spawn_new_piece(void) {
    // ... set current state ...
    is_first_frame = 1;  // Skip erase on first render
}

void render(void) {
    if (!is_first_frame) {
        erase_old_position();
    }
    draw_current_position();
    is_first_frame = 0;
}
```

**3. Force full redraw on spawn**
```c
void spawn_new_piece(void) {
    // ... set current state ...
    needs_full_redraw = 1;  // Redraw everything, no diff
}
```

## Related Samples
- `puzzle` - New tetromino caused flicker until prev_* was synced in spawn

## Notes
This bug is subtle because:
- It only happens on entity transitions (spawn, death, level change)
- The glitch is brief (1 frame)
- Normal movement works fine, masking the root cause
