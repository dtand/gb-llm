# Code Review Standards

> Hard rules for the Reviewer agent when evaluating code changes.

## Purpose

The Reviewer agent examines **only the diff** (changed code) after each Coder step. Its job is to catch bugs before they compound, while keeping context minimal and reviews fast.

## Review Scope

### ✅ MUST Review
- The diff (changed/added lines)
- Immediately surrounding context (5-10 lines)
- Function signatures being modified
- Any new function calls introduced

### ❌ DO NOT Review
- Unchanged files
- Unchanged functions in modified files
- Overall project architecture
- Code style (handled by linter)
- Documentation quality

---

## Severity Levels

### 🔴 CRITICAL (Blocks merge)

Issues that **will definitely** cause crashes, corruption, or major bugs at runtime.

| Category | Examples |
|----------|----------|
| **Crashes** | Division by zero, null pointer dereference, infinite loops |
| **Memory Corruption** | Buffer overflow, out-of-bounds array access |
| **Hardware Violations** | VRAM writes during LCD active, OAM access outside vblank |
| **Resource Exhaustion** | >40 sprites, >8KB WRAM usage, stack overflow |

### 🟡 WARNING (Flag but allow)

Issues that **might** cause problems under certain conditions.

| Category | Examples |
|----------|----------|
| **Edge Cases** | Off-by-one at boundaries, unhandled input combinations |
| **Potential Overflow** | Arithmetic that could overflow with extreme values |
| **Missing Validation** | No bounds check on user input |
| **Race Conditions** | Interrupt handler touching non-volatile variables |

### 🟢 SUGGESTION (Note for future)

Improvements that don't affect correctness.

| Category | Examples |
|----------|----------|
| **Performance** | Could use lookup table, redundant calculation |
| **Clarity** | Magic number could be named constant |
| **Maintainability** | Function doing too many things |

---

## GameBoy-Specific Rules

### CRITICAL: Hardware Timing

```c
// ❌ CRITICAL: VRAM write while LCD is on
set_bkg_tile_xy(x, y, tile);  // Without wait_vbl_done()

// ✅ CORRECT: Wait for vblank first
wait_vbl_done();
set_bkg_tile_xy(x, y, tile);
```

**Rule:** Any VRAM/OAM write (`set_bkg_*`, `set_sprite_*`, `set_win_*`, direct 0x8000-0x9FFF writes) MUST be preceded by `wait_vbl_done()` or be inside a vblank handler.

### CRITICAL: Sprite Limits

```c
// ❌ CRITICAL: Can spawn unlimited enemies
void spawn_enemy(void) {
    enemies[enemy_count++] = new_enemy();  // No limit check!
}

// ✅ CORRECT: Enforce 40 sprite limit
void spawn_enemy(void) {
    if (enemy_count >= MAX_ENEMIES) return;  // MAX_ENEMIES ≤ 40
    enemies[enemy_count++] = new_enemy();
}
```

**Rule:** Total active sprites must never exceed 40. Validate before any `move_sprite()` or sprite allocation.

### CRITICAL: Integer Types

```c
// ❌ CRITICAL: Signed overflow undefined behavior
int8_t x = 100;
x += 50;  // Overflow! -128 to 127 range

// ✅ CORRECT: Use appropriate type
uint8_t x = 100;
x += 50;  // OK, 0-255 range
```

**Rule:** Verify arithmetic cannot overflow the variable's type range.

### CRITICAL: No Dynamic Memory

```c
// ❌ CRITICAL: malloc not available/safe on GB
char* buffer = malloc(100);

// ✅ CORRECT: Static allocation
static char buffer[100];
```

**Rule:** No `malloc`, `calloc`, `realloc`, `free`. All memory must be static.

### CRITICAL: No Floating Point

```c
// ❌ CRITICAL: No FPU on GameBoy
float velocity = 1.5;

// ✅ CORRECT: Fixed-point math
uint8_t velocity = 1;           // Integer
uint16_t velocity_fp = 0x0180;  // 8.8 fixed-point = 1.5
```

**Rule:** No `float`, `double`. Use integers or fixed-point.

### WARNING: Interrupt Safety

```c
// ⚠️ WARNING: Variable modified in interrupt AND main
uint8_t counter;  // Should be volatile

void vblank_isr(void) {
    counter++;
}

void main(void) {
    if (counter > 10) { ... }  // May be optimized incorrectly
}

// ✅ CORRECT: Mark as volatile
volatile uint8_t counter;
```

**Rule:** Variables accessed in both interrupt handlers and main code MUST be `volatile`.

### WARNING: Input Debouncing

```c
// ⚠️ WARNING: No debounce, may trigger multiple times
if (joypad() & J_A) {
    fire_bullet();
}

// ✅ BETTER: Track previous state
uint8_t prev_joy = 0;
uint8_t joy = joypad();
if ((joy & J_A) && !(prev_joy & J_A)) {
    fire_bullet();
}
prev_joy = joy;
```

**Rule:** Button actions should typically use edge detection, not level detection.

---

## Review Checklist

The reviewer MUST check each item against the diff:

### Memory & Types
- [ ] All arrays have bounds checks before access
- [ ] No signed integer overflow possible
- [ ] No use of `malloc`/`free`
- [ ] No floating point types
- [ ] Stack arrays are small (< 128 bytes)

### Hardware
- [ ] VRAM writes only after `wait_vbl_done()`
- [ ] Sprite count stays ≤ 40
- [ ] No writes to read-only registers
- [ ] Interrupt handlers are fast (< 1 scanline)

### Control Flow
- [ ] All loops have exit conditions
- [ ] All switch cases handled (or explicit default)
- [ ] No unreachable code
- [ ] State machines can't get stuck

### Game Logic
- [ ] Player can't move outside screen bounds
- [ ] Collision detection covers all cases
- [ ] Score/lives don't underflow below 0
- [ ] Game over state is reachable and handled

---

## Review Output Format

```json
{
  "approved": true|false,
  "summary": "Brief one-line assessment",
  "issues": [
    {
      "severity": "critical|warning|suggestion",
      "file": "src/game.c",
      "line": 45,
      "code": "enemies[enemy_count++] = ...",
      "issue": "No bounds check on enemy_count",
      "explanation": "Can exceed MAX_ENEMIES (40), causing sprite corruption",
      "fix": "Add: if (enemy_count >= MAX_ENEMIES) return;"
    }
  ],
  "checklist": {
    "memory_safe": true,
    "hardware_safe": false,
    "control_flow_safe": true,
    "game_logic_safe": true
  }
}
```

## Decision Rules

### Approve (approved: true)
- Zero CRITICAL issues
- Any number of WARNINGs or SUGGESTIONs
- Code will compile and run without crashes

### Reject (approved: false)
- One or more CRITICAL issues
- Provide specific fix suggestions
- Coder will receive feedback for revision

---

## Reviewer Boundaries

### DO
- Focus on correctness, not style
- Trust the Coder's architecture decisions
- Be specific about location and fix
- Err on the side of approval for unclear cases

### DON'T
- Rewrite working code
- Suggest refactoring (Refactorer's job)
- Comment on naming or formatting
- Block for theoretical edge cases that are practically impossible

---

## Integration Notes

The Reviewer runs after each Coder step:

```
Coder completes step
       ↓
Reviewer gets: task + diff + touched files
       ↓
   [Approved?]
       ↓ No          ↓ Yes
   Feedback       Continue to
   to Coder       next step
       ↓
   Coder fixes
   (max 2 retries)
```

If Coder fails to fix after 2 attempts, escalate to human review.
