/**
 * @file    sprites.c
 * @brief   Animation frame tile data for Bounce
 * @game    bounce
 * 
 * Contains 4 animation frames for bouncing ball effect.
 */

#include <gb/gb.h>
#include <stdint.h>
#include "sprites.h"

// ============================================================
// ANIMATION FRAME TILES
// ============================================================

/**
 * Ball frame 0: small/compressed
 * 
 *   ........
 *   ........
 *   ..####..
 *   .######.
 *   .######.
 *   ..####..
 *   ........
 *   ........
 */
const uint8_t ball_frame_0[] = {
    0x00, 0x00,
    0x00, 0x00,
    0x3C, 0x3C,
    0x7E, 0x7E,
    0x7E, 0x7E,
    0x3C, 0x3C,
    0x00, 0x00,
    0x00, 0x00
};

/**
 * Ball frame 1: medium
 * 
 *   ........
 *   ..####..
 *   .######.
 *   ########
 *   ########
 *   .######.
 *   ..####..
 *   ........
 */
const uint8_t ball_frame_1[] = {
    0x00, 0x00,
    0x3C, 0x3C,
    0x7E, 0x7E,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0x7E, 0x7E,
    0x3C, 0x3C,
    0x00, 0x00
};

/**
 * Ball frame 2: large/stretched
 * 
 *   ..####..
 *   .######.
 *   ########
 *   ########
 *   ########
 *   ########
 *   .######.
 *   ..####..
 */
const uint8_t ball_frame_2[] = {
    0x3C, 0x3C,
    0x7E, 0x7E,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0x7E, 0x7E,
    0x3C, 0x3C
};

/**
 * Ball frame 3: medium (same as frame 1 for smooth loop)
 */
const uint8_t ball_frame_3[] = {
    0x00, 0x00,
    0x3C, 0x3C,
    0x7E, 0x7E,
    0xFF, 0xFF,
    0xFF, 0xFF,
    0x7E, 0x7E,
    0x3C, 0x3C,
    0x00, 0x00
};

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Load all animation frames into sprite VRAM
 */
void sprites_init(void) {
    // Load all 4 animation frames
    set_sprite_data(TILE_BALL_0, 1, ball_frame_0);
    set_sprite_data(TILE_BALL_1, 1, ball_frame_1);
    set_sprite_data(TILE_BALL_2, 1, ball_frame_2);
    set_sprite_data(TILE_BALL_3, 1, ball_frame_3);
    
    // Initialize sprite to first frame
    set_sprite_tile(SPRITE_BALL, TILE_BALL_0);
}
