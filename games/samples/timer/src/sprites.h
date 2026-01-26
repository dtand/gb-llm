/**
 * @file    sprites.h
 * @brief   Tile declarations for Timer Challenge
 * @game    timer
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// BACKGROUND TILE INDICES
// ============================================================

#define TILE_EMPTY      0
#define TILE_DIGIT_0    1   // Tiles 1-10 are digits 0-9
#define TILE_LETTER_A   11  // Tiles 11-36 are letters A-Z
#define TILE_COLON      37
#define TILE_EXCLAIM    38

// ============================================================
// FUNCTIONS
// ============================================================

void sprites_init(void);

#endif
