/**
 * @file    sprites.h
 * @brief   Tile definitions for Memory Card Game
 * @game    memory
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <stdint.h>

// ============================================================
// BACKGROUND TILE INDICES
// ============================================================

#define TILE_EMPTY      0

// Card back (face-down)
#define TILE_CARD_BACK  1

// Card faces (8 different symbols for pairs)
#define TILE_CARD_STAR      2
#define TILE_CARD_HEART     3
#define TILE_CARD_DIAMOND   4
#define TILE_CARD_CLUB      5
#define TILE_CARD_MOON      6
#define TILE_CARD_SUN       7
#define TILE_CARD_BOLT      8
#define TILE_CARD_SKULL     9

// Matched card (empty/cleared)
#define TILE_CARD_MATCHED   10

// Cursor tiles
#define TILE_CURSOR_TL      11
#define TILE_CURSOR_TR      12
#define TILE_CURSOR_BL      13
#define TILE_CURSOR_BR      14

// UI tiles
#define TILE_DIGIT_0        20
// Digits 0-9 at tiles 20-29

// Letters for text
#define TILE_M              30
#define TILE_O              31
#define TILE_V              32
#define TILE_E              33
#define TILE_S              34
#define TILE_W              35
#define TILE_I              36
#define TILE_N              37
#define TILE_COLON          38
#define TILE_P              39
#define TILE_A              40
#define TILE_R              41
#define TILE_Y              42

// ============================================================
// GRID CONSTANTS
// ============================================================

#define GRID_COLS       4
#define GRID_ROWS       4
#define TOTAL_CARDS     16
#define NUM_PAIRS       8

// Grid position on screen (in tiles)
#define GRID_START_X    4
#define GRID_START_Y    3

// Card size (2x2 tiles each)
#define CARD_WIDTH      2
#define CARD_HEIGHT     2

// Spacing between cards
#define CARD_SPACING_X  3
#define CARD_SPACING_Y  3

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

/**
 * @brief   Initialize all tile data in VRAM
 */
void sprites_init(void);

#endif /* SPRITES_H */
