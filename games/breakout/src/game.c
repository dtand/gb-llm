/**
 * @file    game.c
 * @brief   Core game logic for Breakout
 * @game    breakout
 * 
 * Handles paddle movement, ball physics, brick collision,
 * and scoring system.
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
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state and brick layout
 * 
 * Resets all game variables, fills brick array,
 * positions paddle and ball at starting locations.
 */
void game_init(void) {
    uint8_t row, col;
    
    // Center paddle
    game.paddle_x = SPRITE_OFFSET_X + (SCREEN_WIDTH >> 1) - (PADDLE_WIDTH >> 1);
    
    // Ball starts on paddle, not moving
    game.ball_x = game.paddle_x + (PADDLE_WIDTH >> 1) - (BALL_SIZE >> 1);
    game.ball_y = SPRITE_OFFSET_Y + PADDLE_Y - BALL_SIZE;
    game.ball_dx = BALL_SPEED;
    game.ball_dy = -BALL_SPEED;
    game.ball_active = 0;
    
    // Initialize all bricks as present
    for (row = 0; row < BRICK_ROWS; row++) {
        for (col = 0; col < BRICK_COLS; col++) {
            game.bricks[row][col] = 1;
        }
    }
    game.bricks_remaining = TOTAL_BRICKS;
    
    // Reset score/lives/flags
    game.score = 0;
    game.lives = INITIAL_LIVES;
    game.game_over = 0;
    game.game_won = 0;
    
    // Draw bricks on background
    game_setup_bricks();
}

/**
 * @brief   Set up initial brick layout on background
 * 
 * Draws all brick rows using background tiles.
 * Each brick is 2 tiles wide (16 pixels).
 */
void game_setup_bricks(void) {
    uint8_t row, col;
    uint8_t tile_y, tile_x;
    uint8_t tile_idx;
    
    // Each brick row uses a different tile for visual variety
    for (row = 0; row < BRICK_ROWS; row++) {
        tile_y = (BRICK_START_Y >> 3) + row;  // Convert pixel Y to tile Y
        
        // Use different brick tile based on row (cycles through available)
        tile_idx = TILE_BRICK_1 + (row % 3);
        
        for (col = 0; col < BRICK_COLS; col++) {
            tile_x = col << 1;  // Each brick is 2 tiles wide
            
            if (game.bricks[row][col]) {
                // Draw brick (2 tiles)
                set_bkg_tile_xy(tile_x, tile_y, tile_idx);
                set_bkg_tile_xy(tile_x + 1, tile_y, tile_idx);
            } else {
                // Empty space
                set_bkg_tile_xy(tile_x, tile_y, TILE_EMPTY);
                set_bkg_tile_xy(tile_x + 1, tile_y, TILE_EMPTY);
            }
        }
    }
}

// ============================================================
// INPUT HANDLING
// ============================================================

/**
 * @brief   Read and process joypad input
 * 
 * Moves paddle left/right, launches ball on START.
 */
void game_handle_input(void) {
    prev_input = curr_input;
    curr_input = joypad();
    
    // START: launch ball or restart game
    if ((curr_input & J_START) && !(prev_input & J_START)) {
        if (game.game_over || game.game_won) {
            game_init();
        } else if (!game.ball_active) {
            game.ball_active = 1;
        }
    }
    
    if (game.game_over || game.game_won) {
        return;
    }
    
    // Paddle movement
    if (curr_input & J_LEFT) {
        if (game.paddle_x > PADDLE_MIN_X + PADDLE_SPEED) {
            game.paddle_x -= PADDLE_SPEED;
        } else {
            game.paddle_x = PADDLE_MIN_X;
        }
    }
    if (curr_input & J_RIGHT) {
        if (game.paddle_x < PADDLE_MAX_X - PADDLE_SPEED) {
            game.paddle_x += PADDLE_SPEED;
        } else {
            game.paddle_x = PADDLE_MAX_X;
        }
    }
    
    // If ball not active, keep it on paddle
    if (!game.ball_active) {
        game.ball_x = game.paddle_x + (PADDLE_WIDTH >> 1) - (BALL_SIZE >> 1);
    }
}

// ============================================================
// COLLISION DETECTION
// ============================================================

/**
 * @brief   Check and handle ball-brick collision
 * 
 * Determines which brick the ball hit and destroys it.
 * Updates background tile and score.
 */
static void check_brick_collision(void) {
    int8_t ball_center_x, ball_center_y;
    int8_t brick_row, brick_col;
    uint8_t tile_x, tile_y;
    
    // Get ball center in screen coordinates
    ball_center_x = (game.ball_x - SPRITE_OFFSET_X) + (BALL_SIZE >> 1);
    ball_center_y = (game.ball_y - SPRITE_OFFSET_Y) + (BALL_SIZE >> 1);
    
    // Check if ball is in brick area
    if (ball_center_y < BRICK_START_Y || 
        ball_center_y >= BRICK_START_Y + (BRICK_ROWS * BRICK_HEIGHT)) {
        return;
    }
    
    // Calculate which brick
    brick_row = (ball_center_y - BRICK_START_Y) / BRICK_HEIGHT;
    brick_col = ball_center_x / BRICK_WIDTH;
    
    // Bounds check
    if (brick_row < 0 || brick_row >= BRICK_ROWS ||
        brick_col < 0 || brick_col >= BRICK_COLS) {
        return;
    }
    
    // Check if brick exists
    if (game.bricks[brick_row][brick_col]) {
        // Destroy brick
        game.bricks[brick_row][brick_col] = 0;
        game.bricks_remaining--;
        game.score += (BRICK_ROWS - brick_row);  // Higher rows = more points
        
        // Update background tiles
        tile_y = (BRICK_START_Y >> 3) + brick_row;
        tile_x = brick_col << 1;
        set_bkg_tile_xy(tile_x, tile_y, TILE_EMPTY);
        set_bkg_tile_xy(tile_x + 1, tile_y, TILE_EMPTY);
        
        // Bounce ball (reverse Y direction)
        game.ball_dy = -game.ball_dy;
        
        // Check win condition
        if (game.bricks_remaining == 0) {
            game.game_won = 1;
        }
    }
}

/**
 * @brief   Check and handle ball-paddle collision
 * 
 * Bounces ball upward. Hit position affects angle.
 */
static void check_paddle_collision(void) {
    int8_t relative_x;
    uint8_t paddle_left, paddle_right;
    uint8_t ball_bottom;
    
    // Ball moving down?
    if (game.ball_dy < 0) {
        return;
    }
    
    // Ball bottom edge
    ball_bottom = game.ball_y - SPRITE_OFFSET_Y + BALL_SIZE;
    
    // Check if ball at paddle height
    if (ball_bottom < PADDLE_Y || ball_bottom > PADDLE_Y + PADDLE_HEIGHT) {
        return;
    }
    
    // Check horizontal overlap
    paddle_left = game.paddle_x - SPRITE_OFFSET_X;
    paddle_right = paddle_left + PADDLE_WIDTH;
    
    if (game.ball_x - SPRITE_OFFSET_X + BALL_SIZE > paddle_left &&
        game.ball_x - SPRITE_OFFSET_X < paddle_right) {
        
        // Calculate hit position (-8 to +8 from center)
        relative_x = (game.ball_x - SPRITE_OFFSET_X + (BALL_SIZE >> 1)) - 
                     (paddle_left + (PADDLE_WIDTH >> 1));
        
        // Adjust X velocity based on hit position
        if (relative_x < -4) {
            game.ball_dx = -BALL_SPEED - 1;
        } else if (relative_x > 4) {
            game.ball_dx = BALL_SPEED + 1;
        } else if (relative_x < 0) {
            game.ball_dx = -BALL_SPEED;
        } else {
            game.ball_dx = BALL_SPEED;
        }
        
        // Bounce upward
        game.ball_dy = -BALL_SPEED;
        
        // Push ball above paddle to prevent multiple collisions
        game.ball_y = SPRITE_OFFSET_Y + PADDLE_Y - BALL_SIZE - 1;
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Update ball movement and all collisions
 * 
 * Called once per frame. Moves ball, checks wall/paddle/brick
 * collisions, handles ball loss.
 */
void game_update(void) {
    int16_t new_x, new_y;
    
    if (game.game_over || game.game_won || !game.ball_active) {
        return;
    }
    
    // Calculate new ball position
    new_x = game.ball_x + game.ball_dx;
    new_y = game.ball_y + game.ball_dy;
    
    // Wall collisions (left/right)
    if (new_x <= BALL_MIN_X) {
        new_x = BALL_MIN_X;
        game.ball_dx = -game.ball_dx;
    } else if (new_x >= BALL_MAX_X) {
        new_x = BALL_MAX_X;
        game.ball_dx = -game.ball_dx;
    }
    
    // Ceiling collision
    if (new_y <= BALL_MIN_Y) {
        new_y = BALL_MIN_Y;
        game.ball_dy = -game.ball_dy;
    }
    
    // Ball fell off bottom
    if (new_y >= BALL_MAX_Y) {
        game.lives--;
        if (game.lives == 0) {
            game.game_over = 1;
        } else {
            // Reset ball to paddle
            game.ball_active = 0;
            game.ball_x = game.paddle_x + (PADDLE_WIDTH >> 1) - (BALL_SIZE >> 1);
            game.ball_y = SPRITE_OFFSET_Y + PADDLE_Y - BALL_SIZE;
            game.ball_dy = -BALL_SPEED;
        }
        return;
    }
    
    // Apply new position
    game.ball_x = (uint8_t)new_x;
    game.ball_y = (uint8_t)new_y;
    
    // Check collisions
    check_paddle_collision();
    check_brick_collision();
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Update sprite positions
 * 
 * Positions ball and paddle sprites based on game state.
 */
void game_render(void) {
    // Ball sprite
    move_sprite(SPRITE_BALL, game.ball_x, game.ball_y);
    
    // Paddle sprites (2 sprites for 16px width)
    move_sprite(SPRITE_PADDLE_L, game.paddle_x, SPRITE_OFFSET_Y + PADDLE_Y);
    move_sprite(SPRITE_PADDLE_R, game.paddle_x + 8, SPRITE_OFFSET_Y + PADDLE_Y);
}
