/**
 * @file    sprites.h
 * @brief   Sprite definitions for Melody
 * @game    melody
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// Visual pulse indicator tiles (4 sizes)
#define TILE_PULSE_0    0   // Small
#define TILE_PULSE_1    1
#define TILE_PULSE_2    2
#define TILE_PULSE_3    3   // Large

// Sprite index
#define SPRITE_INDICATOR    0

void sprites_init(void);

#endif
