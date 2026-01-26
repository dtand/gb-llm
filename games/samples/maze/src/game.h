#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include "sprites.h"

// Game states
#define STATE_TITLE         0
#define STATE_GENERATING    1
#define STATE_PLAYING       2
#define STATE_WIN           3

// Directions for maze generation
#define DIR_UP      0
#define DIR_RIGHT   1
#define DIR_DOWN    2
#define DIR_LEFT    3

// Cell states for maze
#define CELL_WALL   0
#define CELL_PATH   1

// Game state structure
typedef struct {
    uint8_t state;
    
    // Maze grid
    uint8_t maze[MAZE_WIDTH][MAZE_HEIGHT];
    
    // Player position (in maze cells)
    uint8_t player_x;
    uint8_t player_y;
    
    // Exit position
    uint8_t exit_x;
    uint8_t exit_y;
    
    // Move counter
    uint16_t moves;
    
    // Level number
    uint8_t level;
    
    // RNG seed
    uint16_t seed;
    
    // Input state
    uint8_t joypad_prev;
} GameState;

extern GameState game;

// Function declarations
void game_init(void);
void game_update(void);
void generate_maze(void);
void draw_maze(void);
void draw_player(void);
void draw_hud(void);
void move_player(int8_t dx, int8_t dy);

#endif
