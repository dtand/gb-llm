/**
 * @file    sprites.c
 * @brief   Sprite tile data and initialization for Pong
 * @game    pong
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
 * Ball tile: 8x8 filled circle
 * 
 * Visual representation:
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
    0x3C, 0x3C,     // Row 0: ..####..
    0x7E, 0x7E,     // Row 1: .######.
    0xFF, 0xFF,     // Row 2: ########
    0xFF, 0xFF,     // Row 3: ########
    0xFF, 0xFF,     // Row 4: ########
    0xFF, 0xFF,     // Row 5: ########
    0x7E, 0x7E,     // Row 6: .######.
    0x3C, 0x3C      // Row 7: ..####..
};

/**
 * Paddle top tile: 8x8 with rounded top corners
 */
const uint8_t paddle_top_tile[] = {
    0x3C, 0x3C,     // Row 0: ..####.. (rounded)
    0x7E, 0x7E,     // Row 1: .######.
    0xFF, 0xFF,     // Row 2: ########
    0xFF, 0xFF,     // Row 3: ########
    0xFF, 0xFF,     // Row 4: ########
    0xFF, 0xFF,     // Row 5: ########
    0xFF, 0xFF,     // Row 6: ########
    0xFF, 0xFF      // Row 7: ########
};

/**
 * Paddle middle tile: 8x8 solid block
 */
const uint8_t paddle_mid_tile[] = {
    0xFF, 0xFF,     // Row 0: ########
    0xFF, 0xFF,     // Row 1: ########
    0xFF, 0xFF,     // Row 2: ########
    0xFF, 0xFF,     // Row 3: ########
    0xFF, 0xFF,     // Row 4: ########
    0xFF, 0xFF,     // Row 5: ########
    0xFF, 0xFF,     // Row 6: ########
    0xFF, 0xFF      // Row 7: ########
};

/**
 * Paddle bottom tile: 8x8 with rounded bottom corners
 */
const uint8_t paddle_bot_tile[] = {
    0xFF, 0xFF,     // Row 0: ########
    0xFF, 0xFF,     // Row 1: ########
    0xFF, 0xFF,     // Row 2: ########
    0xFF, 0xFF,     // Row 3: ########
    0xFF, 0xFF,     // Row 4: ########
    0xFF, 0xFF,     // Row 5: ########
    0x7E, 0x7E,     // Row 6: .######.
    0x3C, 0x3C      // Row 7: ..####.. (rounded)
};

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Load sprite tiles and initialize OAM entries
 * 
 * Loads tile graphics into sprite VRAM and assigns
 * tiles to each sprite in OAM.
 */
void sprites_init(void) {
    // Load tile data into sprite VRAM
    set_sprite_data(TILE_BALL, 1, ball_tile);
    set_sprite_data(TILE_PADDLE_TOP, 1, paddle_top_tile);
    set_sprite_data(TILE_PADDLE_MID, 1, paddle_mid_tile);
    set_sprite_data(TILE_PADDLE_BOT, 1, paddle_bot_tile);
    
    // Assign tiles to sprites
    
    // Ball: single 8x8 sprite
    set_sprite_tile(SPRITE_BALL, TILE_BALL);
    
    // Left paddle: 3 tiles stacked (8x24)
    set_sprite_tile(SPRITE_PADDLE_L, TILE_PADDLE_TOP);
    set_sprite_tile(SPRITE_PADDLE_L + 1, TILE_PADDLE_MID);
    set_sprite_tile(SPRITE_PADDLE_L + 2, TILE_PADDLE_BOT);
    
    // Right paddle: 3 tiles stacked (8x24)
    set_sprite_tile(SPRITE_PADDLE_R, TILE_PADDLE_TOP);
    set_sprite_tile(SPRITE_PADDLE_R + 1, TILE_PADDLE_MID);
    set_sprite_tile(SPRITE_PADDLE_R + 2, TILE_PADDLE_BOT);
}
