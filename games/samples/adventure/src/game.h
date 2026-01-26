/**
 * @file    game.h
 * @brief   Game state and constants for Top-Down Adventure
 * @game    adventure
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// CONSTANTS
// ============================================================

// Map dimensions (in tiles)
#define MAP_WIDTH           20
#define MAP_HEIGHT          18

// Player movement
#define MOVE_DELAY          8   // @tunable range:2-16 step:2 desc:"Frames between moves (lower=faster)"

// Tile types
#define TILE_FLOOR          0
#define TILE_WALL           1
#define TILE_TREE           2
#define TILE_PATH           3
#define TILE_DOOR           4

// Directions
#define DIR_DOWN            0
#define DIR_UP              1
#define DIR_LEFT            2
#define DIR_RIGHT           3

// ============================================================
// TYPES
// ============================================================

/**
 * @brief   Player state
 */
typedef struct {
    uint8_t tile_x;         // Position in tiles
    uint8_t tile_y;
    uint8_t pixel_x;        // Position in pixels (for sprite)
    uint8_t pixel_y;
    uint8_t direction;      // Facing direction
    uint8_t move_timer;     // Movement cooldown
} Player;

/**
 * @brief   NPC state
 */
typedef struct {
    uint8_t tile_x;
    uint8_t tile_y;
    uint8_t active;
} NPC;

/**
 * @brief   Game state
 */
typedef struct {
    Player player;
    NPC npc;
    uint8_t dialog_active;
    uint8_t dialog_timer;
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
