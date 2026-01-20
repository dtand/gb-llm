/**
 * @file    sprites.h
 * @brief   Sprite and tile definitions for Pong
 * @game    pong
 * 
 * Defines tile indices in VRAM and sprite indices in OAM.
 * 
 * Sprite allocation:
 *   0     - Ball (8x8)
 *   1,2,3 - Left paddle (8x24, 3 tiles)
 *   4,5,6 - Right paddle (8x24, 3 tiles)
 * 
 * Total: 7 sprites used (max 40 available, max 10 per scanline)
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// TILE INDICES (in VRAM)
// ============================================================

#define TILE_BALL           0
#define TILE_PADDLE_TOP     1
#define TILE_PADDLE_MID     2
#define TILE_PADDLE_BOT     3

// ============================================================
// SPRITE INDICES (in OAM)
// ============================================================

#define SPRITE_BALL         0

#define SPRITE_PADDLE_L     1   // Uses sprites 1, 2, 3
#define SPRITE_PADDLE_R     4   // Uses sprites 4, 5, 6

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

/** @brief Load sprite tiles and initialize OAM entries */
void sprites_init(void);

#endif
