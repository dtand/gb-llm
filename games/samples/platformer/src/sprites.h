/**
 * @file    sprites.h
 * @brief   Sprite and tile declarations for Platformer
 * @game    platformer
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// BACKGROUND TILE INDICES
// ============================================================

#define TILE_EMPTY      0
#define TILE_PLATFORM   1

// ============================================================
// SPRITE TILE INDICES
// ============================================================

#define TILE_PLAYER     0

// ============================================================
// SPRITE INDICES (OAM slots)
// ============================================================

#define SPRITE_PLAYER   0

// ============================================================
// FUNCTIONS
// ============================================================

void sprites_init(void);

#endif
