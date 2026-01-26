# Timer Challenge

A reaction time test game demonstrating **timer interrupts** and **interrupt handlers** for precise timing.

## Features Demonstrated

- **Timer Interrupt**: Hardware timer for millisecond-accurate measurement
- **Interrupt Handlers**: Custom ISR registration with GBDK
- **Random Delays**: Unpredictable wait times to prevent anticipation
- **Number Display**: Multi-digit millisecond display

## Controls

| Button | Action |
|--------|--------|
| START | Begin game |
| A | React when "GO!" appears |

## Gameplay

1. Press START to begin
2. Wait for "GO!" to appear (random 1-3 second delay)
3. Press A as fast as possible
4. Your reaction time is displayed in milliseconds
5. Press A to try again

**Warning**: Pressing A before "GO!" appears counts as a false start!

## Technical Notes

### Timer Registers

The GameBoy has a timer system controlled by these registers:

| Register | Address | Purpose |
|----------|---------|---------|
| DIV | 0xFF04 | Divider (increments at 16384 Hz) |
| TIMA | 0xFF05 | Timer counter (triggers interrupt on overflow) |
| TMA | 0xFF06 | Timer modulo (TIMA resets to this value) |
| TAC | 0xFF07 | Timer control (enable + clock select) |

### TAC Clock Speeds

| TAC bits 1-0 | Clock | Frequency |
|--------------|-------|-----------|
| 00 | CPU/1024 | 4096 Hz |
| 01 | CPU/16 | 262144 Hz |
| 10 | CPU/64 | 65536 Hz |
| 11 | CPU/256 | 16384 Hz |

### Interrupt Setup (GBDK)

```c
// Register timer interrupt handler
void timer_isr(void) {
    // Called when TIMA overflows
    milliseconds++;
}

// In main:
add_TIM(timer_isr);     // Register handler
TMA_REG = 0x00;         // Modulo value
TAC_REG = 0x07;         // Enable, 16384 Hz
set_interrupts(VBL_IFLAG | TIM_IFLAG);
```

## Build

```bash
make        # Build ROM
make run    # Build and run in SameBoy
make clean  # Remove build artifacts
```
