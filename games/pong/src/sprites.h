#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// Tile indices in VRAM
#define TILE_BALL       0
#define TILE_PADDLE     1   // Uses tiles 1, 2, 3 for 8x24 paddle

// Sprite indices in OAM
#define SPRITE_BALL     0
#define SPRITE_PADDLE_L 1   // Uses sprites 1, 2, 3
#define SPRITE_PADDLE_R 4   // Uses sprites 4, 5, 6

// Function declarations
void init_sprites(void);

#endif
