/**
 * @file    sprites.c
 * @brief   Tile data and initialization for Breakout
 * @game    breakout
 * 
 * Contains graphics data for sprites and background tiles.
 * All tile data is stored in ROM (const).
 */

#include <gb/gb.h>
#include <stdint.h>
#include "sprites.h"

// ============================================================
// BACKGROUND TILE DATA (stored in ROM)
// ============================================================

/**
 * Empty tile: completely blank
 */
const uint8_t empty_tile[] = {
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00
};

/**
 * Brick tile variant 1: solid with border
 * 
 * Visual:
 *   ########
 *   #......#
 *   #......#
 *   #......#
 *   #......#
 *   #......#
 *   #......#
 *   ########
 */
const uint8_t brick_tile_1[] = {
    0xFF, 0xFF,     // ########
    0x81, 0xFF,     // #......#
    0x81, 0xFF,     // #......#
    0x81, 0xFF,     // #......#
    0x81, 0xFF,     // #......#
    0x81, 0xFF,     // #......#
    0x81, 0xFF,     // #......#
    0xFF, 0xFF      // ########
};

/**
 * Brick tile variant 2: lighter fill
 * 
 * Visual:
 *   ########
 *   #.#.#.##
 *   ##.#.#.#
 *   #.#.#.##
 *   ##.#.#.#
 *   #.#.#.##
 *   ##.#.#.#
 *   ########
 */
const uint8_t brick_tile_2[] = {
    0xFF, 0xFF,     // ########
    0xAB, 0xFF,     // #.#.#.##
    0xD5, 0xFF,     // ##.#.#.#
    0xAB, 0xFF,     // #.#.#.##
    0xD5, 0xFF,     // ##.#.#.#
    0xAB, 0xFF,     // #.#.#.##
    0xD5, 0xFF,     // ##.#.#.#
    0xFF, 0xFF      // ########
};

/**
 * Brick tile variant 3: horizontal lines
 * 
 * Visual:
 *   ########
 *   ........
 *   ########
 *   ........
 *   ########
 *   ........
 *   ########
 *   ########
 */
const uint8_t brick_tile_3[] = {
    0xFF, 0xFF,     // ########
    0x00, 0xFF,     // ........
    0xFF, 0xFF,     // ########
    0x00, 0xFF,     // ........
    0xFF, 0xFF,     // ########
    0x00, 0xFF,     // ........
    0xFF, 0xFF,     // ########
    0xFF, 0xFF      // ########
};

// ============================================================
// SPRITE TILE DATA (stored in ROM)
// ============================================================

/**
 * Ball tile: 8x8 circle
 * 
 * Visual:
 *   ..####..
 *   .######.
 *   ########
 *   ########
 *   ########
 *   ########
 *   .######.
 *   ..####..
 */
const uint8_t ball_tile[] = {
    0x3C, 0x3C,     // ..####..
    0x7E, 0x7E,     // .######.
    0xFF, 0xFF,     // ########
    0xFF, 0xFF,     // ########
    0xFF, 0xFF,     // ########
    0xFF, 0xFF,     // ########
    0x7E, 0x7E,     // .######.
    0x3C, 0x3C      // ..####..
};

/**
 * Paddle tile: 8x8 rectangle
 * 
 * Visual:
 *   ########
 *   ########
 *   ########
 *   ########
 *   ########
 *   ########
 *   ########
 *   ########
 */
const uint8_t paddle_tile[] = {
    0xFF, 0xFF,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0xFF, 0xFF
};

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Load all tiles and initialize sprites
 * 
 * Loads background tiles into BKG VRAM and sprite
 * tiles into sprite VRAM. Sets up sprite tile assignments.
 */
void sprites_init(void) {
    // Load background tiles
    set_bkg_data(TILE_EMPTY, 1, empty_tile);
    set_bkg_data(TILE_BRICK_1, 1, brick_tile_1);
    set_bkg_data(TILE_BRICK_2, 1, brick_tile_2);
    set_bkg_data(TILE_BRICK_3, 1, brick_tile_3);
    
    // Load sprite tiles
    set_sprite_data(TILE_BALL, 1, ball_tile);
    set_sprite_data(TILE_PADDLE, 1, paddle_tile);
    
    // Assign tiles to sprites
    set_sprite_tile(SPRITE_BALL, TILE_BALL);
    set_sprite_tile(SPRITE_PADDLE_L, TILE_PADDLE);
    set_sprite_tile(SPRITE_PADDLE_R, TILE_PADDLE);
}
