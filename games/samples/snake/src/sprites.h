/**
 * @file    sprites.h
 * @brief   Sprite and tile definitions for Snake
 * @game    snake
 * 
 * Defines tile indices in VRAM and sprite indices in OAM.
 * 
 * Sprite allocation:
 *   0-9  - Snake body segments (head + up to 9 body)
 *   10   - Food item
 * 
 * Total: 11 sprites used (max 40 available, max 10 per scanline)
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// TILE INDICES (in VRAM)
// ============================================================

#define TILE_SNAKE_HEAD     0
#define TILE_SNAKE_BODY     1
#define TILE_FOOD           2

// ============================================================
// SPRITE LIMITS
// ============================================================

#define MAX_SNAKE_SPRITES   10      // Max visible snake segments
#define SPRITE_FOOD         10      // Food sprite index

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

/** @brief Load sprite tiles and initialize OAM entries */
void sprites_init(void);

#endif
