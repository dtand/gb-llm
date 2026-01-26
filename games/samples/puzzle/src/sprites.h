/**
 * @file    sprites.h
 * @brief   Tile declarations for Falling Block Puzzle
 * @game    puzzle
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// BACKGROUND TILE INDICES
// ============================================================

#define TILE_EMPTY      0   // Empty cell
#define TILE_BLOCK      1   // Locked block
#define TILE_ACTIVE     2   // Current falling piece
#define TILE_WALL       3   // Border wall

// ============================================================
// FUNCTIONS
// ============================================================

void sprites_init(void);

#endif
