/**
 * @file    sprites.c
 * @brief   Tile data and initialization for Runner
 * @game    runner
 */

#include <gb/gb.h>
#include <stdint.h>
#include "sprites.h"

// ============================================================
// BACKGROUND TILES
// ============================================================

const uint8_t empty_tile[] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

/** Ground tile: solid bottom */
const uint8_t ground_tile[] = {
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
};

/** Obstacle tile: spike/block shape */
const uint8_t obstacle_tile[] = {
    0x18, 0x18,     // ...##...
    0x3C, 0x3C,     // ..####..
    0x7E, 0x7E,     // .######.
    0xFF, 0xFF,     // ########
    0xFF, 0xFF,     // ########
    0xFF, 0xFF,     // ########
    0xFF, 0xFF,     // ########
    0xFF, 0xFF      // ########
};

// ============================================================
// SPRITE TILES
// ============================================================

/** Player tile: simple stick figure */
const uint8_t player_tile[] = {
    0x3C, 0x3C,     // ..####.. (head)
    0x3C, 0x3C,     // ..####..
    0x18, 0x18,     // ...##... (neck)
    0x7E, 0x7E,     // .######. (arms)
    0x18, 0x18,     // ...##... (body)
    0x18, 0x18,     // ...##...
    0x24, 0x24,     // ..#..#.. (legs)
    0x42, 0x42      // .#....#.
};

// ============================================================
// INITIALIZATION
// ============================================================

void sprites_init(void) {
    // Load background tiles
    set_bkg_data(TILE_EMPTY, 1, empty_tile);
    set_bkg_data(TILE_GROUND, 1, ground_tile);
    set_bkg_data(TILE_OBSTACLE, 1, obstacle_tile);
    
    // Load sprite tiles
    set_sprite_data(TILE_PLAYER, 1, player_tile);
    
    // Set up player sprite
    set_sprite_tile(SPRITE_PLAYER, TILE_PLAYER);
}
