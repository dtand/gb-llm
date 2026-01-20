/**
 * @file    sprites.h
 * @brief   Sprite and tile definitions for Breakout
 * @game    breakout
 * 
 * Defines tile indices in VRAM and sprite indices in OAM.
 * 
 * Sprite allocation:
 *   0   - Ball
 *   1   - Paddle left half
 *   2   - Paddle right half
 * 
 * Background tiles:
 *   0   - Empty
 *   1-3 - Brick variants (different rows)
 * 
 * Total: 3 sprites, 4 background tiles
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// BACKGROUND TILE INDICES
// ============================================================

#define TILE_EMPTY      0
#define TILE_BRICK_1    1       // Top rows
#define TILE_BRICK_2    2       // Middle rows
#define TILE_BRICK_3    3       // Bottom rows

// ============================================================
// SPRITE TILE INDICES (separate VRAM bank)
// ============================================================

#define TILE_BALL       0
#define TILE_PADDLE     1

// ============================================================
// SPRITE OAM INDICES
// ============================================================

#define SPRITE_BALL         0
#define SPRITE_PADDLE_L     1
#define SPRITE_PADDLE_R     2

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

/** @brief Load all tiles and initialize sprites */
void sprites_init(void);

#endif
