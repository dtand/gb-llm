// Racing - Game Logic Implementation

#include <gb/gb.h>
#include <rand.h>
#include <string.h>
#include "game.h"
#include "sprites.h"

// Global game state
GameState game;

// Track pattern for one "segment" (repeating)
// Each row is: grass, barrier, road, center, road, barrier, grass
static const uint8_t track_row_normal[] = {
    TILE_GRASS, TILE_GRASS, TILE_GRASS,
    TILE_BARRIER_L, 
    TILE_ROAD, TILE_ROAD, TILE_ROAD,
    TILE_ROAD, TILE_ROAD, TILE_ROAD_LINE, TILE_ROAD, TILE_ROAD,
    TILE_ROAD, TILE_ROAD, TILE_ROAD,
    TILE_BARRIER_R,
    TILE_GRASS, TILE_GRASS, TILE_GRASS, TILE_GRASS
};

static const uint8_t track_row_finish[] = {
    TILE_GRASS, TILE_GRASS, TILE_GRASS,
    TILE_BARRIER_L,
    TILE_FINISH_L, TILE_FINISH_R, TILE_FINISH_L, TILE_FINISH_R,
    TILE_FINISH_L, TILE_FINISH_R, TILE_FINISH_L, TILE_FINISH_R,
    TILE_FINISH_L, TILE_FINISH_R, TILE_FINISH_L,
    TILE_BARRIER_R,
    TILE_GRASS, TILE_GRASS, TILE_GRASS, TILE_GRASS
};

// ===========================================
// INITIALIZATION
// ===========================================

void game_init(void) {
    uint8_t i, row;
    
    // Initialize game state
    game.player_x = 80;         // Center of screen
    game.player_y = 120;        // Lower portion of screen
    game.speed = 0;
    game.scroll_pos = 0;
    game.distance = 8;          // Start past the finish line position
    game.lap = 1;
    game.crossed_line = 0;
    game.time_frames = 0;
    game.time_sec = 0;
    game.time_tenths = 0;
    game.state = STATE_COUNTDOWN;
    game.countdown = 3;
    game.countdown_timer = 60;  // 1 second per count
    
    // Clear obstacles
    for (i = 0; i < MAX_OBSTACLES; i++) {
        game.obstacles[i].active = 0;
        game.obstacles[i].x = 0;
        game.obstacles[i].y = 0;
    }
    
    // Initialize random seed
    initrand(DIV_REG);
    
    // Draw initial track - fill ALL 32 rows of VRAM background
    // This prevents garbage/white tiles from appearing on first load
    for (row = 0; row < 32; row++) {
        draw_track_row(row, row + 8);
    }
    
    // Reset scroll register
    SCY_REG = 0;
    
    // Setup player sprite (2x2 metasprite)
    set_sprite_tile(0, 0);
    set_sprite_tile(1, 1);
    set_sprite_tile(2, 2);
    set_sprite_tile(3, 3);
    
    // Setup obstacle sprites
    set_sprite_tile(4, 4);
    set_sprite_tile(5, 5);
    set_sprite_tile(6, 6);
    set_sprite_tile(7, 7);
    
    // Hide obstacles initially
    move_sprite(4, 0, 0);
    move_sprite(5, 0, 0);
    move_sprite(6, 0, 0);
    move_sprite(7, 0, 0);
    
    // Setup window layer for HUD (fixed, doesn't scroll)
    move_win(7, 136);  // Position window at bottom (y=136 means 8 pixels of window)
    
    // Initialize HUD on window layer
    draw_hud();
    
    SHOW_SPRITES;
    SHOW_BKG;
    SHOW_WIN;
}

// ===========================================
// TRACK RENDERING
// ===========================================

void draw_track_row(uint8_t screen_row, uint8_t track_row) {
    // Determine if this is a finish line row
    uint8_t is_finish = (track_row % TRACK_ROWS) == FINISH_LINE_ROW ||
                        (track_row % TRACK_ROWS) == (FINISH_LINE_ROW + 1);
    
    if (is_finish) {
        set_bkg_tiles(0, screen_row, 20, 1, track_row_finish);
    } else {
        set_bkg_tiles(0, screen_row, 20, 1, track_row_normal);
    }
}

void update_scroll(void) {
    static uint16_t last_tile_pos = 0;
    uint16_t tile_pos;
    uint8_t new_row;
    
    // Update scroll position based on speed
    game.scroll_pos += game.speed;
    
    // Calculate tile position (divide by 128 = 8 pixels * 16 subpixels)
    tile_pos = game.scroll_pos >> 7;
    
    // Check if we've scrolled to a new tile row
    if (tile_pos != last_tile_pos) {
        // Draw new row at the bottom of visible area (wrapping in VRAM)
        new_row = (tile_pos + 17) & 0x1F;
        draw_track_row(new_row, tile_pos + 17 + 8);  // +8 for initial offset
        last_tile_pos = tile_pos;
        
        // Track distance for lap counting
        game.distance++;
        
        // Check for lap completion (crossing finish line)
        if ((game.distance % TRACK_ROWS) == FINISH_LINE_ROW) {
            if (!game.crossed_line) {
                game.crossed_line = 1;
                game.lap++;
                if (game.lap > LAP_TOTAL) {
                    game.state = STATE_FINISHED;
                }
            }
        } else if ((game.distance % TRACK_ROWS) == (FINISH_LINE_ROW + 4)) {
            game.crossed_line = 0;  // Reset for next lap
        }
    }
    
    // Apply scroll - use full scroll position for smooth scrolling
    // Divide by 16 to get pixel position, negate for "driving north" effect
    SCY_REG = (uint8_t)(-(game.scroll_pos >> 4));
}

// ===========================================
// OBSTACLE MANAGEMENT  
// ===========================================

void spawn_obstacle(void) {
    uint8_t i;
    uint8_t lane;
    
    for (i = 0; i < MAX_OBSTACLES; i++) {
        if (!game.obstacles[i].active) {
            lane = rand() % 3;  // 0, 1, or 2
            game.obstacles[i].x = 48 + (lane * 32);  // Lane positions
            game.obstacles[i].y = -16;               // Start above screen
            game.obstacles[i].active = 1;
            game.obstacles[i].lane = lane;
            break;
        }
    }
}

void update_obstacles(void) {
    uint8_t i;
    int16_t rel_speed;
    static uint8_t spawn_timer = 0;
    
    // Spawn new obstacles periodically
    spawn_timer++;
    if (spawn_timer > 90 && game.speed > 2) {
        spawn_timer = 0;
        spawn_obstacle();
    }
    
    // Update each obstacle
    for (i = 0; i < MAX_OBSTACLES; i++) {
        if (game.obstacles[i].active) {
            // Obstacle moves down relative to player speed
            // Faster player = obstacles come at you faster
            rel_speed = game.speed - 2;  // Obstacles have base speed of 2
            if (rel_speed < 1) rel_speed = 1;
            
            game.obstacles[i].y += rel_speed;
            
            // Deactivate if off screen
            if (game.obstacles[i].y > 160) {
                game.obstacles[i].active = 0;
                // Hide sprites
                move_sprite(4 + (i * 4), 0, 0);
                move_sprite(5 + (i * 4), 0, 0);
                move_sprite(6 + (i * 4), 0, 0);
                move_sprite(7 + (i * 4), 0, 0);
            }
        }
    }
}

uint8_t check_collision(void) {
    uint8_t i;
    int16_t dx, dy;
    
    for (i = 0; i < MAX_OBSTACLES; i++) {
        if (game.obstacles[i].active) {
            dx = game.player_x - game.obstacles[i].x;
            dy = game.player_y - game.obstacles[i].y;
            
            // Simple AABB collision (16x16 hitbox)
            if (dx < 0) dx = -dx;
            if (dy < 0) dy = -dy;
            
            if (dx < 14 && dy < 14) {
                return 1;  // Collision!
            }
        }
    }
    return 0;
}

// ===========================================
// INPUT HANDLING
// ===========================================

void game_handle_input(void) {
    uint8_t keys = joypad();
    
    if (game.state == STATE_RACING) {
        // Steering
        if (keys & J_LEFT) {
            game.player_x -= 2;
            if (game.player_x < PLAYER_MIN_X) {
                game.player_x = PLAYER_MIN_X;
            }
        }
        if (keys & J_RIGHT) {
            game.player_x += 2;
            if (game.player_x > PLAYER_MAX_X) {
                game.player_x = PLAYER_MAX_X;
            }
        }
        
        // Acceleration (A button)
        if (keys & J_A) {
            if (game.speed < SPEED_MAX) {
                game.speed += ACCEL_RATE;
                if (game.speed > SPEED_MAX) game.speed = SPEED_MAX;
            }
        } else {
            // Natural deceleration
            if (game.speed > 0) {
                game.speed--;
            }
        }
        
        // Brake (B button)
        if (keys & J_B) {
            if (game.speed > BRAKE_RATE) {
                game.speed -= BRAKE_RATE;
            } else {
                game.speed = 0;
            }
        }
    }
    else if (game.state == STATE_FINISHED) {
        // Restart
        if (keys & J_START) {
            game_init();
        }
    }
}

// ===========================================
// HUD DRAWING
// ===========================================

void draw_number(uint8_t x, uint8_t y, uint16_t num, uint8_t digits) {
    uint8_t i;
    uint8_t tile;
    uint16_t divisor = 1;
    
    // Calculate divisor for leftmost digit
    for (i = 1; i < digits; i++) {
        divisor *= 10;
    }
    
    // Draw each digit on window layer
    for (i = 0; i < digits; i++) {
        tile = TILE_DIGIT_0 + ((num / divisor) % 10);
        set_win_tile_xy(x + i, y, tile);
        divisor /= 10;
    }
}

void draw_number_bkg(uint8_t x, uint8_t y, uint16_t num, uint8_t digits) {
    uint8_t i;
    uint8_t tile;
    uint16_t divisor = 1;
    
    // Calculate divisor for leftmost digit
    for (i = 1; i < digits; i++) {
        divisor *= 10;
    }
    
    // Draw each digit on background layer
    for (i = 0; i < digits; i++) {
        tile = TILE_DIGIT_0 + ((num / divisor) % 10);
        set_bkg_tile_xy(x + i, y, tile);
        divisor /= 10;
    }
}

void draw_hud(void) {
    // Use window layer for fixed HUD (doesn't scroll)
    
    // LAP display (left side)
    set_win_tile_xy(0, 0, TILE_LETTER_L);
    set_win_tile_xy(1, 0, TILE_LETTER_A);
    set_win_tile_xy(2, 0, TILE_LETTER_P);
    
    // Current lap / total
    if (game.lap <= LAP_TOTAL) {
        draw_number(3, 0, game.lap, 1);
    } else {
        draw_number(3, 0, LAP_TOTAL, 1);
    }
    set_win_tile_xy(4, 0, TILE_SLASH);
    draw_number(5, 0, LAP_TOTAL, 1);
    
    // TIME display (center)
    set_win_tile_xy(7, 0, TILE_LETTER_T);
    set_win_tile_xy(8, 0, TILE_LETTER_I);
    set_win_tile_xy(9, 0, TILE_LETTER_M);
    set_win_tile_xy(10, 0, TILE_LETTER_E);
    
    // Time value (seconds)
    draw_number(11, 0, game.time_sec, 2);
    
    // Speed indicator (right side)
    set_win_tile_xy(13, 0, TILE_LETTER_S);
    set_win_tile_xy(14, 0, TILE_LETTER_P);
    set_win_tile_xy(15, 0, TILE_LETTER_D);
    draw_number(16, 0, game.speed, 2);
}

// ===========================================
// GAME UPDATE
// ===========================================

void game_update(void) {
    uint8_t i;
    
    switch (game.state) {
        case STATE_COUNTDOWN:
            game.countdown_timer--;
            if (game.countdown_timer == 0) {
                game.countdown_timer = 60;
                game.countdown--;
                if (game.countdown == 0) {
                    game.state = STATE_RACING;
                }
            }
            // Draw countdown in center
            if (game.countdown > 0) {
                set_bkg_tile_xy(9, 8, TILE_DIGIT_0 + game.countdown);
                set_bkg_tile_xy(10, 8, TILE_EMPTY);
            } else {
                // "GO" - clear countdown area
                set_bkg_tile_xy(9, 8, TILE_ROAD);
                set_bkg_tile_xy(10, 8, TILE_ROAD);
            }
            break;
            
        case STATE_RACING:
            // Update timer
            game.time_frames++;
            if (game.time_frames >= 6) {  // ~10 tenths per second at 60fps
                game.time_frames = 0;
                game.time_tenths++;
                if (game.time_tenths >= 10) {
                    game.time_tenths = 0;
                    game.time_sec++;
                    if (game.time_sec > 99) game.time_sec = 99;
                }
            }
            
            // Update scroll based on speed
            if (game.speed > 0) {
                update_scroll();
            }
            
            // Update obstacles
            update_obstacles();
            
            // Check collision
            if (check_collision()) {
                // Slow down on collision
                game.speed = game.speed / 2;
            }
            break;
            
        case STATE_FINISHED:
            // Display "FINISH" message
            set_bkg_tile_xy(5, 8, TILE_LETTER_F);
            set_bkg_tile_xy(6, 8, TILE_LETTER_I);
            set_bkg_tile_xy(7, 8, TILE_LETTER_N);
            set_bkg_tile_xy(8, 8, TILE_LETTER_I);
            set_bkg_tile_xy(9, 8, TILE_LETTER_S);
            set_bkg_tile_xy(10, 8, TILE_LETTER_H);
            // Show final time on next line
            set_bkg_tile_xy(5, 9, TILE_LETTER_T);
            set_bkg_tile_xy(6, 9, TILE_LETTER_I);
            set_bkg_tile_xy(7, 9, TILE_LETTER_M);
            set_bkg_tile_xy(8, 9, TILE_LETTER_E);
            set_bkg_tile_xy(9, 9, TILE_COLON);
            draw_number_bkg(10, 9, game.time_sec, 2);
            set_bkg_tile_xy(12, 9, TILE_LETTER_S);
            break;
    }
}

// ===========================================
// DRAW SPRITES
// ===========================================

void game_draw(void) {
    uint8_t i;
    int16_t ox, oy;
    
    // Draw player car (2x2 metasprite)
    move_sprite(0, game.player_x, game.player_y);
    move_sprite(1, game.player_x + 8, game.player_y);
    move_sprite(2, game.player_x, game.player_y + 8);
    move_sprite(3, game.player_x + 8, game.player_y + 8);
    
    // Draw obstacles
    for (i = 0; i < MAX_OBSTACLES; i++) {
        if (game.obstacles[i].active) {
            ox = game.obstacles[i].x;
            oy = game.obstacles[i].y;
            
            // Only draw if on screen
            if (oy > 0 && oy < 160) {
                move_sprite(4, ox, oy);
                move_sprite(5, ox + 8, oy);
                move_sprite(6, ox, oy + 8);
                move_sprite(7, ox + 8, oy + 8);
            }
        }
    }
    
    // Update HUD
    draw_hud();
}
