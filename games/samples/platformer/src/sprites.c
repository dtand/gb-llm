/**
 * @file    sprites.c
 * @brief   Tile data and initialization for Platformer
 * @game    platformer
 */

#include <gb/gb.h>
#include <stdint.h>
#include "sprites.h"

// ============================================================
// BACKGROUND TILES
// ============================================================

/** Empty tile (sky/background) */
const uint8_t empty_tile[] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

/** Platform tile (solid brick pattern) */
const uint8_t platform_tile[] = {
    0xFF, 0xFF, 0x81, 0xFF, 0x81, 0xFF, 0x81, 0xFF,
    0xFF, 0xFF, 0x18, 0xFF, 0x18, 0xFF, 0x18, 0xFF
};

// ============================================================
// SPRITE TILES
// ============================================================

/** Player character (simple square guy) */
const uint8_t player_tile[] = {
    0x3C, 0x3C,     // ..####.. (head top)
    0x7E, 0x42,     // .######. (face with eyes)
    0xFF, 0x5A,     // ######## (eyes/face)
    0x7E, 0x7E,     // .######. (chin)
    0x3C, 0x3C,     // ..####.. (neck/body)
    0x7E, 0x7E,     // .######. (body)
    0x66, 0x66,     // .##..##. (legs)
    0x66, 0x66      // .##..##. (feet)
};

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize all sprite and background tiles
 */
void sprites_init(void) {
    // Load background tiles
    set_bkg_data(TILE_EMPTY, 1, empty_tile);
    set_bkg_data(TILE_PLATFORM, 1, platform_tile);
    
    // Load sprite tiles
    set_sprite_data(TILE_PLAYER, 1, player_tile);
    
    // Set up player sprite
    set_sprite_tile(SPRITE_PLAYER, TILE_PLAYER);
}
