/**
 * @file    game.c
 * @brief   Core game logic for Platformer
 * @game    platformer
 * 
 * Demonstrates platform collision and variable jump height.
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

// ============================================================
// LEVEL DATA
// ============================================================

// Level map: 0 = empty, 1 = platform
// 20 columns x 18 rows
const uint8_t level_map[18][20] = {
    // Row 0 (top)
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    // Row 2-3: high platform
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    // Row 4-5
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    // Row 6-7
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0},
    // Row 8-9
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    // Row 10-11: mid platform
    {0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    // Row 12-13
    {0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    // Row 14-15: lower platforms
    {0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    {0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0},
    // Row 16-17: ground
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
    {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}
};

// ============================================================
// LEVEL FUNCTIONS
// ============================================================

/**
 * @brief   Draw the level from map data
 */
static void draw_level(void) {
    uint8_t x, y;
    
    for (y = 0; y < 18; y++) {
        for (x = 0; x < 20; x++) {
            if (level_map[y][x] == 1) {
                set_bkg_tile_xy(x, y, TILE_PLATFORM);
            } else {
                set_bkg_tile_xy(x, y, TILE_EMPTY);
            }
        }
    }
}

/**
 * @brief   Check if a tile position is solid
 */
static uint8_t is_solid(uint8_t tile_x, uint8_t tile_y) {
    if (tile_x >= 20 || tile_y >= 18) {
        return 0;  // Out of bounds = not solid
    }
    return level_map[tile_y][tile_x] == 1;
}

/**
 * @brief   Check for ground beneath player
 */
static uint8_t check_ground(uint8_t px, int16_t py) {
    uint8_t tile_x_left, tile_x_right, tile_y;
    
    // Check tile below player's feet
    // Player feet Y = py + PLAYER_HEIGHT
    tile_y = (py + PLAYER_HEIGHT) >> 3;  // Divide by 8
    
    // Check both corners of player width
    tile_x_left = px >> 3;
    tile_x_right = (px + PLAYER_WIDTH - 1) >> 3;
    
    // Ground if either foot corner is on solid tile
    return is_solid(tile_x_left, tile_y) || is_solid(tile_x_right, tile_y);
}

/**
 * @brief   Check horizontal collision
 */
static uint8_t check_horizontal(uint8_t px, int16_t py) {
    uint8_t tile_x, tile_y_top, tile_y_bottom;
    
    tile_x = px >> 3;
    tile_y_top = py >> 3;
    tile_y_bottom = (py + PLAYER_HEIGHT - 1) >> 3;
    
    return is_solid(tile_x, tile_y_top) || is_solid(tile_x, tile_y_bottom);
}

/**
 * @brief   Check for ceiling above player (when jumping up)
 */
static uint8_t check_ceiling(uint8_t px, int16_t py) {
    uint8_t tile_x_left, tile_x_right, tile_y;
    
    // Check tile above player's head
    tile_y = py >> 3;  // Divide by 8
    
    // Check both corners of player width
    tile_x_left = px >> 3;
    tile_x_right = (px + PLAYER_WIDTH - 1) >> 3;
    
    // Ceiling if either top corner hits solid tile
    return is_solid(tile_x_left, tile_y) || is_solid(tile_x_right, tile_y);
}

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state
 */
void game_init(void) {
    game.player_x = PLAYER_START_X;
    game.player_y = PLAYER_START_Y;
    game.velocity_y = 0;
    game.on_ground = 0;
    game.jumping = 0;
    game.jump_held = 0;
    game.jump_timer = 0;
    
    draw_level();
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
        game_init();
        return;
    }
    
    // Horizontal movement
    if (curr_input & J_LEFT) {
        if (game.player_x > MIN_X + PLAYER_SPEED) {
            uint8_t new_x = game.player_x - PLAYER_SPEED;
            // Check collision on left side
            if (!check_horizontal(new_x, game.player_y)) {
                game.player_x = new_x;
            }
        } else {
            game.player_x = MIN_X;
        }
    }
    
    if (curr_input & J_RIGHT) {
        if (game.player_x < MAX_X - PLAYER_SPEED) {
            uint8_t new_x = game.player_x + PLAYER_SPEED;
            // Check collision on right side
            if (!check_horizontal(new_x + PLAYER_WIDTH, game.player_y)) {
                game.player_x = new_x;
            }
        } else {
            game.player_x = MAX_X;
        }
    }
    
    // Jump - only start when on ground and A just pressed
    if ((curr_input & J_A) && !(prev_input & J_A) && game.on_ground) {
        game.velocity_y = JUMP_VELOCITY;
        game.on_ground = 0;
        game.jumping = 1;
        game.jump_held = 1;
        game.jump_timer = 0;
    }
    
    // Track if A is still held during jump
    if (game.jumping) {
        if (curr_input & J_A) {
            if (game.jump_timer < MAX_JUMP_HOLD) {
                game.jump_timer++;
            }
        } else {
            // A released, end variable jump boost
            game.jump_held = 0;
        }
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Update game state
 */
void game_update(void) {
    int16_t new_y;
    uint8_t landed;
    uint8_t hit_ceiling;
    
    // Apply gravity
    // If holding A during upward movement and within time limit, reduce gravity
    if (game.jumping && game.jump_held && game.velocity_y < 0 && game.jump_timer < MAX_JUMP_HOLD) {
        // Holding A and still rising - slightly reduced gravity for higher jump
        // Still apply gravity, just less of it
        if ((game.jump_timer & 1) == 0) {  // Apply gravity every other frame
            game.velocity_y += GRAVITY;
        }
    } else {
        // Normal gravity
        game.velocity_y += GRAVITY;
    }
    
    // Clamp to terminal velocity
    if (game.velocity_y > TERMINAL_VELOCITY) {
        game.velocity_y = TERMINAL_VELOCITY;
    }
    
    // Apply velocity
    new_y = game.player_y + game.velocity_y;
    
    // Check ceiling collision when rising (jumping up)
    if (game.velocity_y < 0) {
        hit_ceiling = check_ceiling(game.player_x, new_y);
        
        if (hit_ceiling) {
            // Hit ceiling - stop upward movement
            uint8_t tile_y = new_y >> 3;
            game.player_y = ((tile_y + 1) << 3);  // Snap to below the ceiling tile
            game.velocity_y = 0;  // Stop rising, start falling
            game.jump_held = 0;   // End variable jump
        } else {
            game.player_y = new_y;
        }
    }
    // Check ground collision when falling
    else if (game.velocity_y >= 0) {
        landed = check_ground(game.player_x, new_y);
        
        if (landed) {
            // Snap to top of platform
            uint8_t tile_y = (new_y + PLAYER_HEIGHT) >> 3;
            game.player_y = (tile_y << 3) - PLAYER_HEIGHT;
            game.velocity_y = 0;
            game.on_ground = 1;
            game.jumping = 0;
            game.jump_held = 0;
        } else {
            game.player_y = new_y;
            game.on_ground = 0;
        }
    }
    
    // Clamp to screen boundaries
    if (game.player_y < MIN_Y) {
        game.player_y = MIN_Y;
        game.velocity_y = 0;
    }
    if (game.player_y > MAX_Y) {
        game.player_y = MAX_Y;
        game.velocity_y = 0;
        game.on_ground = 1;
        game.jumping = 0;
    }
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Render game
 */
void game_render(void) {
    // Update player sprite position
    move_sprite(SPRITE_PLAYER, 
                game.player_x + SPRITE_X_OFFSET, 
                (uint8_t)game.player_y + SPRITE_Y_OFFSET);
}
