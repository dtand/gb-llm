/**
 * @file    sprites.h
 * @brief   Sprite and tile declarations for Space Shooter
 * @game    shooter
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// BACKGROUND TILE INDICES
// ============================================================

#define TILE_EMPTY      0
#define TILE_STAR       1

// HUD text tiles
#define TILE_DIGIT_0    2   // Tiles 2-11 are digits 0-9
#define TILE_S          12
#define TILE_C          13
#define TILE_L          14
#define TILE_V          15
#define TILE_COLON      16

// ============================================================
// SPRITE TILE INDICES
// ============================================================

// Player ship metasprite (4 tiles for 16x16)
#define TILE_SHIP_TL    0   // Top-left
#define TILE_SHIP_TR    1   // Top-right
#define TILE_SHIP_BL    2   // Bottom-left
#define TILE_SHIP_BR    3   // Bottom-right

#define TILE_BULLET     4
#define TILE_ENEMY      5

// ============================================================
// SPRITE INDICES (OAM slots)
// ============================================================

// Player uses sprites 0-3 (metasprite)
#define SPRITE_PLAYER       0

// Bullets use sprites 4-7
#define SPRITE_BULLET_BASE  4

// Enemies use sprites 8-11
#define SPRITE_ENEMY_BASE   8

// ============================================================
// FUNCTIONS
// ============================================================

void sprites_init(void);

#endif
