/**
 * @file    game.h
 * @brief   Game state and constants for Space Shooter
 * @game    shooter
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// CONSTANTS
// ============================================================

// Screen dimensions (in pixels)
#define SCREEN_WIDTH        160
#define SCREEN_HEIGHT       144

// Sprite coordinate offsets (sprites have 8,16 offset)
#define SPRITE_X_OFFSET     8
#define SPRITE_Y_OFFSET     16

// Player ship (16x16 metasprite)
#define PLAYER_WIDTH        16
#define PLAYER_HEIGHT       16
#define PLAYER_START_X      72      // Centered horizontally
#define PLAYER_START_Y      120     // Near bottom
#define PLAYER_SPEED        2       // @tunable range:1-4 step:1 desc:"Ship movement speed"
#define PLAYER_MIN_X        8       // Left boundary
#define PLAYER_MAX_X        (SCREEN_WIDTH - PLAYER_WIDTH)

// Bullets
#define MAX_BULLETS         4       // @tunable range:2-8 step:1 desc:"Max bullets on screen"
#define BULLET_SPEED        4       // @tunable range:2-8 step:1 desc:"Bullet travel speed"
#define BULLET_WIDTH        4
#define BULLET_HEIGHT       8

// Enemies
#define MAX_ENEMIES         4       // @tunable range:2-8 step:1 desc:"Max enemies on screen"
#define ENEMY_WIDTH         8
#define ENEMY_HEIGHT        8
#define ENEMY_SPEED         1       // @tunable range:1-4 step:1 desc:"Default enemy speed"
#define ENEMY_SPAWN_RATE    60      // @tunable range:30-120 step:15 desc:"Frames between spawns"

// Window/HUD
#define HUD_HEIGHT          16      // 2 tile rows
#define WINDOW_X            7       // WX offset (7 = left edge)
#define WINDOW_Y            0       // Top of screen

// Scrolling
#define SCROLL_SPEED        1       // @tunable range:1-3 step:1 desc:"Starfield scroll speed"

// ============================================================
// TYPES
// ============================================================

/**
 * @brief   Bullet entity
 */
typedef struct {
    uint8_t x;
    uint8_t y;
    uint8_t active;
} Bullet;

/**
 * @brief   Enemy entity
 */
typedef struct {
    uint8_t x;
    uint8_t y;
    uint8_t active;
} Enemy;

/**
 * @brief   Main game state
 */
typedef struct {
    // Player state
    uint8_t player_x;
    uint8_t player_y;
    uint8_t lives;
    
    // Bullets
    Bullet bullets[MAX_BULLETS];
    
    // Enemies
    Enemy enemies[MAX_ENEMIES];
    uint8_t spawn_timer;
    
    // Scrolling
    uint8_t scroll_y;
    
    // Score
    uint16_t score;
    
    // State flags
    uint8_t game_over;
} GameState;

extern GameState game;
extern uint8_t prev_input;
extern uint8_t curr_input;

// ============================================================
// FUNCTIONS
// ============================================================

void game_init(void);
void game_handle_input(void);
void game_update(void);
void game_render(void);

#endif
