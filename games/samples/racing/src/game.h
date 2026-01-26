// Racing - Game Logic Header

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>

// ===========================================
// GAME STATES
// ===========================================

#define STATE_TITLE     0
#define STATE_COUNTDOWN 1
#define STATE_RACING    2
#define STATE_FINISHED  3

// ===========================================
// TRACK CONSTANTS
// ===========================================

#define TRACK_ROWS      32      // @tunable range:24-64 step:8 desc:"Virtual track height in tiles (lap distance)"
#define FINISH_LINE_ROW 4       // Row where finish line appears
#define LAP_TOTAL       3       // @tunable range:1-5 step:1 desc:"Number of laps to complete the race"

// ===========================================
// OBSTACLE SYSTEM
// ===========================================

#define MAX_OBSTACLES   2       // @tunable range:1-4 step:1 desc:"Maximum simultaneous obstacles"
#define OBSTACLE_SPACING 80     // @tunable range:40-120 step:20 desc:"Minimum pixels between obstacles"

typedef struct {
    int16_t x;                  // X position (pixels)
    int16_t y;                  // Y position (pixels)  
    uint8_t active;             // Is obstacle on screen?
    uint8_t lane;               // Which lane (0-2)
} Obstacle;

// ===========================================
// GAME STATE
// ===========================================

typedef struct {
    // Player state
    int16_t player_x;           // Player X position (pixels)
    int16_t player_y;           // Player Y position (fixed)
    uint8_t speed;              // Current speed (0-8)
    
    // Track state
    uint16_t scroll_pos;        // Track scroll position
    uint16_t distance;          // Distance traveled
    uint8_t lap;                // Current lap (1-3)
    uint8_t crossed_line;       // Has crossed finish this lap?
    
    // Obstacles
    Obstacle obstacles[MAX_OBSTACLES];
    
    // Timing
    uint16_t time_frames;       // Frame counter for time
    uint8_t time_sec;           // Seconds
    uint8_t time_tenths;        // Tenths of seconds
    
    // Game flow
    uint8_t state;              // Current game state
    uint8_t countdown;          // Countdown value (3,2,1,GO)
    uint8_t countdown_timer;    // Frames until next count
    
} GameState;

// ===========================================
// FUNCTION DECLARATIONS
// ===========================================

void game_init(void);
void game_update(void);
void game_handle_input(void);
void game_draw(void);

// Track rendering
void draw_track_row(uint8_t screen_row, uint8_t track_row);
void update_scroll(void);

// Obstacle management
void spawn_obstacle(void);
void update_obstacles(void);
uint8_t check_collision(void);

// HUD
void draw_hud(void);
void draw_number(uint8_t x, uint8_t y, uint16_t num, uint8_t digits);

// Global game state
extern GameState game;

#endif
