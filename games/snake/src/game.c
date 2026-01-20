/**
 * @file    game.c
 * @brief   Core game logic for Snake
 * @game    snake
 * 
 * Handles snake movement, growth, collision detection,
 * food spawning, and game state management.
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

// Random number generator state
static uint16_t rng_state = 12345;
static uint8_t frame_count = 0;

// ============================================================
// RANDOM NUMBER GENERATION
// ============================================================

/**
 * @brief   Get pseudo-random number (0-255)
 * 
 * Uses Linear Congruential Generator (LCG).
 * Seed is mixed with frame count for variety.
 */
uint8_t random_byte(void) {
    // LCG: next = (a * current + c) mod m
    // Using a=13, c=101 for reasonable distribution
    rng_state = rng_state * 13 + 101 + frame_count;
    return (uint8_t)(rng_state >> 8);
}

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state to starting values
 * 
 * Places snake in center of screen, sets initial direction,
 * spawns first food item.
 */
void game_init(void) {
    uint8_t i;
    uint8_t start_x = GRID_WIDTH >> 1;      // Center X
    uint8_t start_y = GRID_HEIGHT >> 1;     // Center Y
    
    // Initialize snake in center, facing right
    game.head_idx = SNAKE_START_LENGTH - 1;
    game.tail_idx = 0;
    game.length = SNAKE_START_LENGTH;
    
    // Place initial body segments (horizontal line)
    for (i = 0; i < SNAKE_START_LENGTH; i++) {
        game.body[i].x = start_x - (SNAKE_START_LENGTH - 1) + i;
        game.body[i].y = start_y;
    }
    
    // Start moving right
    game.direction = DIR_RIGHT;
    game.next_direction = DIR_RIGHT;
    game.move_timer = MOVE_DELAY;
    
    // Reset score and flags
    game.score = 0;
    game.game_over = 0;
    game.paused = 0;
    
    // Spawn first food
    game_spawn_food();
}

/**
 * @brief   Spawn food at random empty position
 * 
 * Generates random positions until finding one
 * not occupied by the snake.
 */
void game_spawn_food(void) {
    uint8_t valid = 0;
    uint8_t attempts = 0;
    uint8_t i, idx;
    
    while (!valid && attempts < 100) {
        // Generate random grid position
        game.food.x = random_byte() % GRID_WIDTH;
        game.food.y = random_byte() % GRID_HEIGHT;
        
        // Check if position is empty (not on snake)
        valid = 1;
        idx = game.tail_idx;
        for (i = 0; i < game.length; i++) {
            if (game.body[idx].x == game.food.x && 
                game.body[idx].y == game.food.y) {
                valid = 0;
                break;
            }
            idx = (idx + 1) % SNAKE_MAX_LENGTH;
        }
        attempts++;
    }
}

// ============================================================
// INPUT HANDLING
// ============================================================

/**
 * @brief   Read and store current joypad input
 * 
 * Buffers direction changes to prevent 180° turns.
 * Handles START for pause/restart.
 */
void game_handle_input(void) {
    prev_input = curr_input;
    curr_input = joypad();
    
    // Mix button presses into RNG
    rng_state += curr_input;
    
    // START: pause toggle or restart
    if ((curr_input & J_START) && !(prev_input & J_START)) {
        if (game.game_over) {
            game_init();
        } else {
            game.paused = !game.paused;
        }
    }
    
    if (game.paused || game.game_over) {
        return;
    }
    
    // Buffer direction change (prevent 180° turn)
    if (curr_input & J_UP) {
        if (game.direction != DIR_DOWN) {
            game.next_direction = DIR_UP;
        }
    } else if (curr_input & J_DOWN) {
        if (game.direction != DIR_UP) {
            game.next_direction = DIR_DOWN;
        }
    } else if (curr_input & J_LEFT) {
        if (game.direction != DIR_RIGHT) {
            game.next_direction = DIR_LEFT;
        }
    } else if (curr_input & J_RIGHT) {
        if (game.direction != DIR_LEFT) {
            game.next_direction = DIR_RIGHT;
        }
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Check if snake head collides with its body
 * 
 * @return  1 if collision detected, 0 otherwise
 */
static uint8_t check_self_collision(void) {
    uint8_t i, idx;
    Position head = game.body[game.head_idx];
    
    // Check against all body segments except head
    idx = game.tail_idx;
    for (i = 0; i < game.length - 1; i++) {
        if (game.body[idx].x == head.x && game.body[idx].y == head.y) {
            return 1;
        }
        idx = (idx + 1) % SNAKE_MAX_LENGTH;
    }
    return 0;
}

/**
 * @brief   Move snake one step in current direction
 * 
 * Updates the circular buffer, checks collisions,
 * handles food eating and growth.
 */
static void move_snake(void) {
    Position new_head;
    uint8_t ate_food = 0;
    
    // Apply buffered direction
    game.direction = game.next_direction;
    
    // Calculate new head position
    new_head = game.body[game.head_idx];
    
    switch (game.direction) {
        case DIR_UP:
            if (new_head.y == 0) {
                game.game_over = 1;
                return;
            }
            new_head.y--;
            break;
        case DIR_DOWN:
            if (new_head.y >= GRID_HEIGHT - 1) {
                game.game_over = 1;
                return;
            }
            new_head.y++;
            break;
        case DIR_LEFT:
            if (new_head.x == 0) {
                game.game_over = 1;
                return;
            }
            new_head.x--;
            break;
        case DIR_RIGHT:
            if (new_head.x >= GRID_WIDTH - 1) {
                game.game_over = 1;
                return;
            }
            new_head.x++;
            break;
    }
    
    // Check food collision before updating body
    if (new_head.x == game.food.x && new_head.y == game.food.y) {
        ate_food = 1;
        game.score++;
        game_spawn_food();
    }
    
    // Add new head to buffer
    game.head_idx = (game.head_idx + 1) % SNAKE_MAX_LENGTH;
    game.body[game.head_idx] = new_head;
    
    if (ate_food) {
        // Grow: don't move tail
        if (game.length < SNAKE_MAX_LENGTH) {
            game.length++;
        }
    } else {
        // Don't grow: move tail forward
        game.tail_idx = (game.tail_idx + 1) % SNAKE_MAX_LENGTH;
    }
    
    // Check self collision (after adding new head)
    if (check_self_collision()) {
        game.game_over = 1;
    }
}

/**
 * @brief   Update all game logic
 * 
 * Called once per frame. Handles movement timing
 * and delegates to move_snake when timer expires.
 */
void game_update(void) {
    frame_count++;
    
    if (game.paused || game.game_over) {
        return;
    }
    
    // Movement timing
    game.move_timer--;
    if (game.move_timer == 0) {
        game.move_timer = MOVE_DELAY;
        move_snake();
    }
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Update sprite positions to match game state
 * 
 * Renders snake body segments and food.
 * Uses sprite cycling for snakes longer than sprite limit.
 */
void game_render(void) {
    uint8_t i, idx;
    uint8_t sprite_num = 0;
    uint8_t screen_x, screen_y;
    
    // Render snake body (up to MAX_VISIBLE_SEGMENTS sprites)
    idx = game.head_idx;
    for (i = 0; i < game.length && sprite_num < MAX_SNAKE_SPRITES; i++) {
        screen_x = SCREEN_LEFT + (game.body[idx].x * GRID_SIZE);
        screen_y = SCREEN_TOP + (game.body[idx].y * GRID_SIZE);
        
        if (i == 0) {
            // Head uses different tile
            set_sprite_tile(sprite_num, TILE_SNAKE_HEAD);
        } else {
            set_sprite_tile(sprite_num, TILE_SNAKE_BODY);
        }
        move_sprite(sprite_num, screen_x, screen_y);
        
        sprite_num++;
        // Move backwards through circular buffer
        idx = (idx == 0) ? SNAKE_MAX_LENGTH - 1 : idx - 1;
    }
    
    // Hide unused snake sprites
    for (i = sprite_num; i < MAX_SNAKE_SPRITES; i++) {
        move_sprite(i, 0, 0);   // Move off-screen
    }
    
    // Render food
    screen_x = SCREEN_LEFT + (game.food.x * GRID_SIZE);
    screen_y = SCREEN_TOP + (game.food.y * GRID_SIZE);
    move_sprite(SPRITE_FOOD, screen_x, screen_y);
}
