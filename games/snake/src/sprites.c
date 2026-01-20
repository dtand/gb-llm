/**
 * @file    sprites.c
 * @brief   Sprite tile data and initialization for Snake
 * @game    snake
 * 
 * Contains tile graphics data and sprite setup code.
 * All tile data is stored in ROM (const).
 */

#include <gb/gb.h>
#include <stdint.h>
#include "sprites.h"

// ============================================================
// TILE DATA (stored in ROM)
// ============================================================

/**
 * Snake head tile: 8x8 with eyes
 * 
 * Visual representation:
 *   .######.
 *   ########
 *   ##.##.##
 *   ########
 *   ########
 *   ########
 *   ########
 *   .######.
 */
const uint8_t snake_head_tile[] = {
    0x7E, 0x7E,     // Row 0: .######.
    0xFF, 0xFF,     // Row 1: ########
    0xDB, 0xDB,     // Row 2: ##.##.## (eyes)
    0xFF, 0xFF,     // Row 3: ########
    0xFF, 0xFF,     // Row 4: ########
    0xFF, 0xFF,     // Row 5: ########
    0xFF, 0xFF,     // Row 6: ########
    0x7E, 0x7E      // Row 7: .######.
};

/**
 * Snake body tile: 8x8 rounded square
 * 
 * Visual representation:
 *   .######.
 *   ########
 *   ########
 *   ########
 *   ########
 *   ########
 *   ########
 *   .######.
 */
const uint8_t snake_body_tile[] = {
    0x7E, 0x7E,     // Row 0: .######.
    0xFF, 0xFF,     // Row 1: ########
    0xFF, 0xFF,     // Row 2: ########
    0xFF, 0xFF,     // Row 3: ########
    0xFF, 0xFF,     // Row 4: ########
    0xFF, 0xFF,     // Row 5: ########
    0xFF, 0xFF,     // Row 6: ########
    0x7E, 0x7E      // Row 7: .######.
};

/**
 * Food tile: 8x8 apple/dot shape
 * 
 * Visual representation:
 *   ...##...
 *   ..####..
 *   .######.
 *   ########
 *   ########
 *   .######.
 *   ..####..
 *   ...##...
 */
const uint8_t food_tile[] = {
    0x18, 0x18,     // Row 0: ...##...
    0x3C, 0x3C,     // Row 1: ..####..
    0x7E, 0x7E,     // Row 2: .######.
    0xFF, 0xFF,     // Row 3: ########
    0xFF, 0xFF,     // Row 4: ########
    0x7E, 0x7E,     // Row 5: .######.
    0x3C, 0x3C,     // Row 6: ..####..
    0x18, 0x18      // Row 7: ...##...
};

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Load sprite tiles and initialize OAM entries
 * 
 * Loads tile graphics into sprite VRAM and assigns
 * initial tiles to sprites.
 */
void sprites_init(void) {
    uint8_t i;
    
    // Load tile data into sprite VRAM
    set_sprite_data(TILE_SNAKE_HEAD, 1, snake_head_tile);
    set_sprite_data(TILE_SNAKE_BODY, 1, snake_body_tile);
    set_sprite_data(TILE_FOOD, 1, food_tile);
    
    // Initialize snake sprites (all start as body, head set during render)
    for (i = 0; i < MAX_SNAKE_SPRITES; i++) {
        set_sprite_tile(i, TILE_SNAKE_BODY);
    }
    
    // Initialize food sprite
    set_sprite_tile(SPRITE_FOOD, TILE_FOOD);
}
