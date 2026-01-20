/**
 * @file    game.c
 * @brief   Core game logic for Runner
 * @game    runner
 * 
 * Demonstrates hardware scrolling using SCX register.
 */

#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"

// ============================================================
// GLOBAL STATE
// ============================================================

GameState game;
uint8_t prev_input = 0;
uint8_t curr_input = 0;

// Obstacle positions in tile X coordinates (0-31)
// These repeat every 32 tiles due to wrapping
static const uint8_t obstacle_positions[] = {10, 18, 25};
#define NUM_OBSTACLES 3

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state
 */
void game_init(void) {
    game.player_y = GROUND_Y;
    game.velocity_y = 0;
    game.on_ground = 1;
    game.scroll_x = 0;
    game.score = 0;
    game.game_over = 0;
    
    game_setup_background();
    
    // Reset scroll register
    SCX_REG = 0;
}

/**
 * @brief   Set up the background tile map
 * 
 * Clears screen and creates ground with obstacles in the 32x32 tile map.
 */
void game_setup_background(void) {
    uint8_t x, y, i;
    uint8_t is_obstacle;
    
    // Clear entire visible area (20x18 tiles) plus extra for scrolling
    for (y = 0; y < 18; y++) {
        for (x = 0; x < BKG_MAP_WIDTH; x++) {
            set_bkg_tile_xy(x, y, TILE_EMPTY);
        }
    }
    
    // Draw ground row with obstacles
    for (x = 0; x < BKG_MAP_WIDTH; x++) {
        // Check if this X is an obstacle position
        is_obstacle = 0;
        for (i = 0; i < NUM_OBSTACLES; i++) {
            if (x == obstacle_positions[i]) {
                is_obstacle = 1;
                break;
            }
        }
        
        if (is_obstacle) {
            // Obstacle above ground
            set_bkg_tile_xy(x, GROUND_TILE_Y - 1, TILE_OBSTACLE);
            set_bkg_tile_xy(x, GROUND_TILE_Y, TILE_GROUND);
        } else {
            set_bkg_tile_xy(x, GROUND_TILE_Y, TILE_GROUND);
        }
    }
}

// ============================================================
// INPUT HANDLING
// ============================================================

/**
 * @brief   Handle player input
 */
void game_handle_input(void) {
    prev_input = curr_input;
    curr_input = joypad();
    
    // START: restart
    if ((curr_input & J_START) && !(prev_input & J_START)) {
        if (game.game_over) {
            game_init();
        }
    }
    
    if (game.game_over) return;
    
    // A: jump (only when on ground)
    if ((curr_input & J_A) && !(prev_input & J_A)) {
        if (game.on_ground) {
            game.velocity_y = JUMP_VELOCITY;
            game.on_ground = 0;
        }
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Check collision with obstacles
 * 
 * Uses scroll position to determine which obstacles
 * are currently near the player.
 */
static uint8_t check_obstacle_collision(void) {
    uint8_t i;
    uint8_t player_tile_x;
    uint8_t player_screen_bottom;
    uint8_t obstacle_screen_top;
    
    // Player is at fixed X, convert to tile considering scroll
    // Player sprite X in background coordinates (subtract sprite offset 8)
    player_tile_x = (PLAYER_X - 8 + game.scroll_x) >> 3;
    
    // Player bottom edge in screen coordinates
    // Sprite Y has +16 offset, so screen Y = sprite_Y - 16
    // Bottom = top + height = (sprite_Y - 16) + 8
    player_screen_bottom = (uint8_t)game.player_y - 16 + PLAYER_HEIGHT;
    
    // Obstacle is at tile row (GROUND_TILE_Y - 1), top of obstacle in screen coords
    obstacle_screen_top = (GROUND_TILE_Y - 1) * 8;  // = 15 * 8 = 120
    
    for (i = 0; i < NUM_OBSTACLES; i++) {
        // Check if obstacle is at player's X position
        if ((player_tile_x & 0x1F) == obstacle_positions[i]) {
            // Check if player's bottom is below obstacle top
            if (player_screen_bottom > obstacle_screen_top) {
                return 1;
            }
        }
    }
    
    return 0;
}

// Gravity accumulator for slower falling
static uint8_t gravity_timer = 0;

/**
 * @brief   Update game state
 */
void game_update(void) {
    if (game.game_over) return;
    
    // Apply gravity every 4 frames for floatier jump
    gravity_timer++;
    if (gravity_timer >= 4) {
        gravity_timer = 0;
        if (game.velocity_y < 4) {  // Terminal velocity
            game.velocity_y += 1;
        }
    }
    
    game.player_y += game.velocity_y;
    
    // Ground collision
    if (game.player_y >= GROUND_Y) {
        game.player_y = GROUND_Y;
        game.velocity_y = 0;
        game.on_ground = 1;
    }
    
    // Update scroll (hardware handles wrapping at 256)
    game.scroll_x += SCROLL_SPEED;
    SCX_REG = game.scroll_x;
    
    // Check obstacle collision
    if (check_obstacle_collision()) {
        game.game_over = 1;
    }
    
    // Increment score
    game.score++;
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Update sprite positions
 */
void game_render(void) {
    move_sprite(SPRITE_PLAYER, PLAYER_X, (uint8_t)game.player_y);
}
