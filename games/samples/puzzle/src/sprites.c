/**
 * @file    sprites.c
 * @brief   Tile data and initialization for Falling Block Puzzle
 * @game    puzzle
 */

#include <gb/gb.h>
#include <stdint.h>
#include "sprites.h"

// ============================================================
// BACKGROUND TILES
// ============================================================

/** Empty cell - light background */
const uint8_t empty_tile[] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

/** Locked block - solid with border */
const uint8_t block_tile[] = {
    0xFF, 0xFF, 0x81, 0xFF, 0x81, 0xFF, 0x81, 0xFF,
    0x81, 0xFF, 0x81, 0xFF, 0x81, 0xFF, 0xFF, 0xFF
};

/** Active piece - different pattern to distinguish */
const uint8_t active_tile[] = {
    0xFF, 0xFF, 0xC3, 0xFF, 0xA5, 0xFF, 0x99, 0xFF,
    0x99, 0xFF, 0xA5, 0xFF, 0xC3, 0xFF, 0xFF, 0xFF
};

/** Wall tile - solid border */
const uint8_t wall_tile[] = {
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
};

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize all background tiles
 */
void sprites_init(void) {
    set_bkg_data(TILE_EMPTY, 1, empty_tile);
    set_bkg_data(TILE_BLOCK, 1, block_tile);
    set_bkg_data(TILE_ACTIVE, 1, active_tile);
    set_bkg_data(TILE_WALL, 1, wall_tile);
}
