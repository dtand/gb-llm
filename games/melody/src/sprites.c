/**
 * @file    sprites.c
 * @brief   Visual indicator tiles for Melody
 * @game    melody
 */

#include <gb/gb.h>
#include <stdint.h>
#include "sprites.h"

// ============================================================
// PULSE INDICATOR TILES
// ============================================================

/** Pulse 0: tiny dot */
const uint8_t pulse_0[] = {
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x18, 0x18,
    0x18, 0x18,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00
};

/** Pulse 1: small */
const uint8_t pulse_1[] = {
    0x00, 0x00,
    0x00, 0x00,
    0x18, 0x18,
    0x3C, 0x3C,
    0x3C, 0x3C,
    0x18, 0x18,
    0x00, 0x00,
    0x00, 0x00
};

/** Pulse 2: medium */
const uint8_t pulse_2[] = {
    0x00, 0x00,
    0x3C, 0x3C,
    0x7E, 0x7E,
    0x7E, 0x7E,
    0x7E, 0x7E,
    0x7E, 0x7E,
    0x3C, 0x3C,
    0x00, 0x00
};

/** Pulse 3: large */
const uint8_t pulse_3[] = {
    0x3C, 0x3C,
    0x7E, 0x7E,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0x7E, 0x7E,
    0x3C, 0x3C
};

// ============================================================
// INITIALIZATION
// ============================================================

void sprites_init(void) {
    set_sprite_data(TILE_PULSE_0, 1, pulse_0);
    set_sprite_data(TILE_PULSE_1, 1, pulse_1);
    set_sprite_data(TILE_PULSE_2, 1, pulse_2);
    set_sprite_data(TILE_PULSE_3, 1, pulse_3);
    
    set_sprite_tile(SPRITE_INDICATOR, TILE_PULSE_0);
}
