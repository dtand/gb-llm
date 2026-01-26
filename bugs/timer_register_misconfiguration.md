# Timer Register Misconfiguration

## Category
Hardware Registers / Interrupts

## Description
Timer-based features run at wrong speed - either way too slow (events barely trigger) or too fast (overflow). Common when implementing frame-independent timing, reaction games, or music tempo.

## Symptoms
- Timer triggers much slower than expected
- Millisecond counters are inaccurate
- Music plays at wrong tempo
- Reaction time shows wrong values

## Root Cause
The TAC (Timer Control) register's clock select bits choose the input frequency. Using the wrong value gives drastically different timing.

```c
// BAD: TAC_REG = 0x04 
// Clock select = 00 = 4096 Hz
// TMA_REG = 0 means overflow every 256 ticks
// Actual frequency: 4096 / 256 = ~16 Hz (way too slow!)

TAC_REG = 0x04;  // 0x04 = timer ON, clock 00
```

## TAC Register Reference

```
TAC_REG bits:
  Bit 2: Timer enable (1 = on, 0 = off)
  Bits 1-0: Clock select
  
Clock select values:
  00 (0x04): 4096 Hz    → ~16 overflows/sec with TMA=0
  01 (0x05): 262144 Hz  → ~1024 overflows/sec with TMA=0  
  10 (0x06): 65536 Hz   → ~256 overflows/sec with TMA=0
  11 (0x07): 16384 Hz   → ~64 overflows/sec with TMA=0
```

## Prevention

**1. Use correct TAC value for desired frequency**
```c
// For ~1ms resolution (1024 Hz):
TMA_REG = 0;      // Overflow every 256 ticks
TAC_REG = 0x05;   // Enable + 262144 Hz clock
// 262144 / 256 = 1024 Hz ≈ ~1ms per tick
```

**2. Document the math**
```c
// Timer configuration for millisecond timing:
// Base clock: 262144 Hz (TAC bits 1-0 = 01)
// TMA (modulo): 0 means count 256 before overflow
// Overflow frequency: 262144 / 256 = 1024 Hz
// Each overflow ≈ 0.977ms (close enough to 1ms)
#define TIMER_FREQ_HZ 1024
TMA_REG = 0;
TAC_REG = 0x05;  // Enable (bit 2) + clock 01 (bits 1-0)
```

**3. Verify with test output**
```c
// Debug: count overflows for 60 frames, should be ~1024
volatile uint16_t debug_count = 0;
// ... in timer ISR: debug_count++;
// ... after 60 frames, debug_count should be ~1024
```

## Common Configurations

| Use Case | TMA | TAC | Frequency |
|----------|-----|-----|-----------|
| ~1ms timing | 0 | 0x05 | 1024 Hz |
| ~4ms timing | 0 | 0x04 | 16 Hz |
| Music tempo 120 BPM | 0 | 0x07 | 64 Hz |
| Fast events | 0 | 0x05 | 1024 Hz |

## Related Samples
- `timer` - Reaction time was inaccurate until TAC_REG changed from 0x04 to 0x05

## Notes
Always verify timer behavior empirically. The GameBoy's 4.19 MHz clock can have slight variations that affect timing calculations.
