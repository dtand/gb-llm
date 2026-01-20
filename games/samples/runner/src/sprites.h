/**
 * @file    sprites.h
 * @brief   Sprite and tile definitions for Runner
 * @game    runner
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// Background tiles
#define TILE_EMPTY      0
#define TILE_GROUND     1
#define TILE_OBSTACLE   2

// Sprite tiles
#define TILE_PLAYER     0

// Sprite indices
#define SPRITE_PLAYER   0

void sprites_init(void);

#endif
