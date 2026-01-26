// Racing - Sprite and Tile Definitions
// Top-down racing with scrolling track

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>

// ===========================================
// TILE INDICES - Background tiles
// ===========================================

// Track tiles
#define TILE_EMPTY          0
#define TILE_ROAD           1
#define TILE_ROAD_LINE      2   // Center line marker
#define TILE_GRASS          3
#define TILE_BARRIER_L      4   // Left barrier
#define TILE_BARRIER_R      5   // Right barrier
#define TILE_FINISH_L       6   // Finish line left
#define TILE_FINISH_R       7   // Finish line right
#define TILE_CHEVRON        8   // Track direction indicator

// HUD tiles  
#define TILE_DIGIT_0        10
#define TILE_DIGIT_9        19
#define TILE_LETTER_L       20  // LAP
#define TILE_LETTER_A       21
#define TILE_LETTER_P       22
#define TILE_LETTER_S       23  // SPEED / SEC
#define TILE_LETTER_E       24
#define TILE_LETTER_D       25
#define TILE_LETTER_T       26  // TIME
#define TILE_LETTER_I       27
#define TILE_LETTER_M       28
#define TILE_LETTER_C       29
#define TILE_COLON          30
#define TILE_SLASH          31
#define TILE_LETTER_F       32  // FINISH
#define TILE_LETTER_N       33
#define TILE_LETTER_H       34

// ===========================================
// SPRITE INDICES - OAM sprites
// ===========================================

#define SPRITE_CAR_0        0   // Player car (2x2 = 4 tiles)
#define SPRITE_CAR_1        1
#define SPRITE_CAR_2        2
#define SPRITE_CAR_3        3
#define SPRITE_OBSTACLE_0   4   // Obstacle car
#define SPRITE_OBSTACLE_1   5
#define SPRITE_OBSTACLE_2   6
#define SPRITE_OBSTACLE_3   7

// ===========================================
// TRACK CONSTANTS
// ===========================================

#define TRACK_LEFT_EDGE     3   // Leftmost road column (tiles)
#define TRACK_RIGHT_EDGE    16  // Rightmost road column
#define TRACK_WIDTH         14  // Road width in tiles

#define PLAYER_MIN_X        32  // Pixel bounds for player
#define PLAYER_MAX_X        136

// ===========================================
// SPEED CONSTANTS  
// ===========================================

#define SPEED_MIN           0
/** @tunable range:8-24 step:2 desc:"Maximum car speed" */
#define SPEED_MAX           16
/** @tunable range:1-3 step:1 desc:"Acceleration rate" */
#define ACCEL_RATE          1
/** @tunable range:1-4 step:1 desc:"Braking deceleration rate" */
#define BRAKE_RATE          2

// ===========================================
// FUNCTION DECLARATIONS
// ===========================================

void sprites_init(void);

// Tile data arrays (defined in sprites.c)
extern const unsigned char road_tiles[];
extern const unsigned char hud_tiles[];
extern const unsigned char car_sprite[];
extern const unsigned char obstacle_sprite[];

#endif
