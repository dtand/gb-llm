/**
 * @file    game.c
 * @brief   Core game logic for Space Shooter
 * @game    shooter
 * 
 * Demonstrates vertical scrolling, metasprites, and window layer HUD.
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

// Simple pseudo-random number generator
static uint8_t rand_seed = 42;

/**
 * @brief   Generate pseudo-random number 0-255
 */
static uint8_t rand8(void) {
    rand_seed ^= (rand_seed << 3);
    rand_seed ^= (rand_seed >> 5);
    rand_seed ^= (rand_seed << 4);
    return rand_seed;
}

// ============================================================
// HUD FUNCTIONS
// ============================================================

/**
 * @brief   Update score display in window layer
 */
static void update_score_display(void) {
    uint8_t digit;
    uint16_t temp = game.score;
    
    // Display 4-digit score at window position (6, 0)
    // Digits go right to left
    digit = temp % 10;
    set_win_tile_xy(9, 0, TILE_DIGIT_0 + digit);
    temp /= 10;
    
    digit = temp % 10;
    set_win_tile_xy(8, 0, TILE_DIGIT_0 + digit);
    temp /= 10;
    
    digit = temp % 10;
    set_win_tile_xy(7, 0, TILE_DIGIT_0 + digit);
    temp /= 10;
    
    digit = temp % 10;
    set_win_tile_xy(6, 0, TILE_DIGIT_0 + digit);
}

/**
 * @brief   Update lives display in window layer
 */
static void update_lives_display(void) {
    // Display lives at window position (18, 0)
    set_win_tile_xy(18, 0, TILE_DIGIT_0 + game.lives);
}

/**
 * @brief   Set up the window layer HUD
 */
static void setup_hud(void) {
    uint8_t x;
    
    // Clear window row
    for (x = 0; x < 20; x++) {
        set_win_tile_xy(x, 0, TILE_EMPTY);
    }
    
    // "SC:" label at position 3
    set_win_tile_xy(3, 0, TILE_S);
    set_win_tile_xy(4, 0, TILE_C);
    set_win_tile_xy(5, 0, TILE_COLON);
    
    // "LV:" label at position 15
    set_win_tile_xy(15, 0, TILE_L);
    set_win_tile_xy(16, 0, TILE_V);
    set_win_tile_xy(17, 0, TILE_COLON);
    
    // Set window position
    WX_REG = WINDOW_X;
    WY_REG = WINDOW_Y;
    
    update_score_display();
    update_lives_display();
}

// ============================================================
// BACKGROUND FUNCTIONS
// ============================================================

/**
 * @brief   Set up the starfield background
 */
static void setup_starfield(void) {
    uint8_t x, y;
    
    // Fill background with empty tiles and sparse stars
    for (y = 0; y < 32; y++) {
        for (x = 0; x < 32; x++) {
            // Pseudo-random star placement
            if (((x * 7 + y * 13) & 0x1F) == 0) {
                set_bkg_tile_xy(x, y, TILE_STAR);
            } else {
                set_bkg_tile_xy(x, y, TILE_EMPTY);
            }
        }
    }
}

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state
 */
void game_init(void) {
    uint8_t i;
    
    // Player state
    game.player_x = PLAYER_START_X;
    game.player_y = PLAYER_START_Y;
    game.lives = 3;
    
    // Clear bullets
    for (i = 0; i < MAX_BULLETS; i++) {
        game.bullets[i].active = 0;
    }
    
    // Clear enemies
    for (i = 0; i < MAX_ENEMIES; i++) {
        game.enemies[i].active = 0;
    }
    
    game.spawn_timer = ENEMY_SPAWN_RATE;
    game.scroll_y = 0;
    game.score = 0;
    game.game_over = 0;
    
    // Set up background and HUD
    setup_starfield();
    setup_hud();
    
    // Reset scroll register
    SCY_REG = 0;
}

// ============================================================
// INPUT HANDLING
// ============================================================

/**
 * @brief   Handle player input
 */
void game_handle_input(void) {
    uint8_t i;
    
    prev_input = curr_input;
    curr_input = joypad();
    
    // START: restart after game over
    if ((curr_input & J_START) && !(prev_input & J_START)) {
        if (game.game_over) {
            game_init();
            return;
        }
    }
    
    if (game.game_over) return;
    
    // D-pad: move ship
    if (curr_input & J_LEFT) {
        if (game.player_x > PLAYER_MIN_X) {
            game.player_x -= PLAYER_SPEED;
        }
    }
    if (curr_input & J_RIGHT) {
        if (game.player_x < PLAYER_MAX_X) {
            game.player_x += PLAYER_SPEED;
        }
    }
    
    // A: fire bullet
    if ((curr_input & J_A) && !(prev_input & J_A)) {
        // Find inactive bullet slot
        for (i = 0; i < MAX_BULLETS; i++) {
            if (!game.bullets[i].active) {
                game.bullets[i].x = game.player_x + (PLAYER_WIDTH / 2) - 2;
                game.bullets[i].y = game.player_y - 4;
                game.bullets[i].active = 1;
                break;
            }
        }
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Spawn a new enemy at random X position
 */
static void spawn_enemy(void) {
    uint8_t i;
    
    for (i = 0; i < MAX_ENEMIES; i++) {
        if (!game.enemies[i].active) {
            // Random X position within screen bounds
            game.enemies[i].x = (rand8() % (SCREEN_WIDTH - ENEMY_WIDTH - 16)) + 8;
            game.enemies[i].y = HUD_HEIGHT + 8;  // Just below HUD
            game.enemies[i].active = 1;
            break;
        }
    }
}

/**
 * @brief   Check AABB collision between two rectangles
 */
static uint8_t check_collision(
    uint8_t x1, uint8_t y1, uint8_t w1, uint8_t h1,
    uint8_t x2, uint8_t y2, uint8_t w2, uint8_t h2
) {
    return (x1 < x2 + w2) && (x1 + w1 > x2) &&
           (y1 < y2 + h2) && (y1 + h1 > y2);
}

/**
 * @brief   Update bullets
 */
static void update_bullets(void) {
    uint8_t i;
    
    for (i = 0; i < MAX_BULLETS; i++) {
        if (game.bullets[i].active) {
            // Move bullet up
            if (game.bullets[i].y > BULLET_SPEED + HUD_HEIGHT) {
                game.bullets[i].y -= BULLET_SPEED;
            } else {
                // Off screen, deactivate
                game.bullets[i].active = 0;
            }
        }
    }
}

/**
 * @brief   Update enemies and check collisions
 */
static void update_enemies(void) {
    uint8_t i, j;
    
    for (i = 0; i < MAX_ENEMIES; i++) {
        if (game.enemies[i].active) {
            // Move enemy down
            game.enemies[i].y += ENEMY_SPEED;
            
            // Off screen, deactivate
            if (game.enemies[i].y > SCREEN_HEIGHT) {
                game.enemies[i].active = 0;
                continue;
            }
            
            // Check collision with bullets
            for (j = 0; j < MAX_BULLETS; j++) {
                if (game.bullets[j].active) {
                    if (check_collision(
                        game.enemies[i].x, game.enemies[i].y,
                        ENEMY_WIDTH, ENEMY_HEIGHT,
                        game.bullets[j].x, game.bullets[j].y,
                        BULLET_WIDTH, BULLET_HEIGHT
                    )) {
                        // Enemy hit!
                        game.enemies[i].active = 0;
                        game.bullets[j].active = 0;
                        game.score += 10;
                        update_score_display();
                        break;
                    }
                }
            }
            
            // Check collision with player
            if (game.enemies[i].active) {
                if (check_collision(
                    game.enemies[i].x, game.enemies[i].y,
                    ENEMY_WIDTH, ENEMY_HEIGHT,
                    game.player_x, game.player_y,
                    PLAYER_WIDTH, PLAYER_HEIGHT
                )) {
                    // Player hit!
                    game.enemies[i].active = 0;
                    game.lives--;
                    update_lives_display();
                    
                    if (game.lives == 0) {
                        game.game_over = 1;
                    }
                }
            }
        }
    }
}

/**
 * @brief   Update game state
 */
void game_update(void) {
    if (game.game_over) return;
    
    // Scroll starfield
    game.scroll_y += SCROLL_SPEED;
    SCY_REG = game.scroll_y;
    
    // Update entities
    update_bullets();
    update_enemies();
    
    // Spawn timer
    if (game.spawn_timer > 0) {
        game.spawn_timer--;
    } else {
        spawn_enemy();
        game.spawn_timer = ENEMY_SPAWN_RATE;
    }
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Render player metasprite (16x16 from 4 sprites)
 */
static void render_player(void) {
    uint8_t sx = game.player_x + SPRITE_X_OFFSET;
    uint8_t sy = game.player_y + SPRITE_Y_OFFSET;
    
    // 4 sprites in 2x2 arrangement
    // [0][1]
    // [2][3]
    move_sprite(SPRITE_PLAYER + 0, sx,     sy);
    move_sprite(SPRITE_PLAYER + 1, sx + 8, sy);
    move_sprite(SPRITE_PLAYER + 2, sx,     sy + 8);
    move_sprite(SPRITE_PLAYER + 3, sx + 8, sy + 8);
}

/**
 * @brief   Render all bullets
 */
static void render_bullets(void) {
    uint8_t i;
    uint8_t sx, sy;
    
    for (i = 0; i < MAX_BULLETS; i++) {
        if (game.bullets[i].active) {
            sx = game.bullets[i].x + SPRITE_X_OFFSET;
            sy = game.bullets[i].y + SPRITE_Y_OFFSET;
            move_sprite(SPRITE_BULLET_BASE + i, sx, sy);
        } else {
            // Hide inactive bullet
            move_sprite(SPRITE_BULLET_BASE + i, 0, 0);
        }
    }
}

/**
 * @brief   Render all enemies
 */
static void render_enemies(void) {
    uint8_t i;
    uint8_t sx, sy;
    
    for (i = 0; i < MAX_ENEMIES; i++) {
        if (game.enemies[i].active) {
            sx = game.enemies[i].x + SPRITE_X_OFFSET;
            sy = game.enemies[i].y + SPRITE_Y_OFFSET;
            move_sprite(SPRITE_ENEMY_BASE + i, sx, sy);
        } else {
            // Hide inactive enemy
            move_sprite(SPRITE_ENEMY_BASE + i, 0, 0);
        }
    }
}

/**
 * @brief   Render all game elements
 */
void game_render(void) {
    render_player();
    render_bullets();
    render_enemies();
}
