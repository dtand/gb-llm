#include <gb/gb.h>
#include <stdint.h>
#include "sprites.h"

// Ball sprite: 8x8 filled circle
const uint8_t ball_tile[] = {
    0x3C, 0x3C,  // ..####..
    0x7E, 0x7E,  // .######.
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0x7E, 0x7E,  // .######.
    0x3C, 0x3C   // ..####..
};

// Paddle tiles: 8x24 (3 tiles stacked)
// Top tile with rounded corners
const uint8_t paddle_top_tile[] = {
    0x3C, 0x3C,  // ..####..
    0x7E, 0x7E,  // .######.
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF   // ########
};

// Middle tile (solid)
const uint8_t paddle_mid_tile[] = {
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF   // ########
};

// Bottom tile with rounded corners
const uint8_t paddle_bottom_tile[] = {
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0xFF, 0xFF,  // ########
    0x7E, 0x7E,  // .######.
    0x3C, 0x3C   // ..####..
};

void init_sprites(void) {
    // Load tile data into sprite VRAM
    set_sprite_data(TILE_BALL, 1, ball_tile);
    set_sprite_data(TILE_PADDLE, 1, paddle_top_tile);
    set_sprite_data(TILE_PADDLE + 1, 1, paddle_mid_tile);
    set_sprite_data(TILE_PADDLE + 2, 1, paddle_bottom_tile);
    
    // Set up ball sprite
    set_sprite_tile(SPRITE_BALL, TILE_BALL);
    
    // Set up left paddle sprites (3 tiles)
    set_sprite_tile(SPRITE_PADDLE_L, TILE_PADDLE);
    set_sprite_tile(SPRITE_PADDLE_L + 1, TILE_PADDLE + 1);
    set_sprite_tile(SPRITE_PADDLE_L + 2, TILE_PADDLE + 2);
    
    // Set up right paddle sprites (3 tiles)
    set_sprite_tile(SPRITE_PADDLE_R, TILE_PADDLE);
    set_sprite_tile(SPRITE_PADDLE_R + 1, TILE_PADDLE + 1);
    set_sprite_tile(SPRITE_PADDLE_R + 2, TILE_PADDLE + 2);
}
