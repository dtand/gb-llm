/**
 * @file    game.c
 * @brief   Core game logic for Falling Block Puzzle
 * @game    puzzle
 * 
 * Demonstrates grid systems, piece rotation, and line clearing.
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

// Simple RNG
static uint8_t rand_seed = 42;

static uint8_t rand8(void) {
    rand_seed ^= (rand_seed << 3);
    rand_seed ^= (rand_seed >> 5);
    rand_seed ^= (rand_seed << 4);
    return rand_seed;
}

// ============================================================
// PIECE DATA
// ============================================================

// Each piece is 4x4, with 4 rotations
// Stored as [piece_type][rotation][row][col]

const uint8_t pieces[7][4][4][4] = {
    // I piece
    {
        {{0,0,0,0}, {1,1,1,1}, {0,0,0,0}, {0,0,0,0}},
        {{0,0,1,0}, {0,0,1,0}, {0,0,1,0}, {0,0,1,0}},
        {{0,0,0,0}, {0,0,0,0}, {1,1,1,1}, {0,0,0,0}},
        {{0,1,0,0}, {0,1,0,0}, {0,1,0,0}, {0,1,0,0}}
    },
    // O piece (no rotation change)
    {
        {{0,0,0,0}, {0,1,1,0}, {0,1,1,0}, {0,0,0,0}},
        {{0,0,0,0}, {0,1,1,0}, {0,1,1,0}, {0,0,0,0}},
        {{0,0,0,0}, {0,1,1,0}, {0,1,1,0}, {0,0,0,0}},
        {{0,0,0,0}, {0,1,1,0}, {0,1,1,0}, {0,0,0,0}}
    },
    // T piece
    {
        {{0,0,0,0}, {1,1,1,0}, {0,1,0,0}, {0,0,0,0}},
        {{0,1,0,0}, {1,1,0,0}, {0,1,0,0}, {0,0,0,0}},
        {{0,1,0,0}, {1,1,1,0}, {0,0,0,0}, {0,0,0,0}},
        {{0,1,0,0}, {0,1,1,0}, {0,1,0,0}, {0,0,0,0}}
    },
    // S piece
    {
        {{0,0,0,0}, {0,1,1,0}, {1,1,0,0}, {0,0,0,0}},
        {{0,1,0,0}, {0,1,1,0}, {0,0,1,0}, {0,0,0,0}},
        {{0,0,0,0}, {0,1,1,0}, {1,1,0,0}, {0,0,0,0}},
        {{0,1,0,0}, {0,1,1,0}, {0,0,1,0}, {0,0,0,0}}
    },
    // Z piece
    {
        {{0,0,0,0}, {1,1,0,0}, {0,1,1,0}, {0,0,0,0}},
        {{0,0,1,0}, {0,1,1,0}, {0,1,0,0}, {0,0,0,0}},
        {{0,0,0,0}, {1,1,0,0}, {0,1,1,0}, {0,0,0,0}},
        {{0,0,1,0}, {0,1,1,0}, {0,1,0,0}, {0,0,0,0}}
    },
    // L piece
    {
        {{0,0,0,0}, {1,1,1,0}, {1,0,0,0}, {0,0,0,0}},
        {{1,1,0,0}, {0,1,0,0}, {0,1,0,0}, {0,0,0,0}},
        {{0,0,1,0}, {1,1,1,0}, {0,0,0,0}, {0,0,0,0}},
        {{0,1,0,0}, {0,1,0,0}, {0,1,1,0}, {0,0,0,0}}
    },
    // J piece
    {
        {{0,0,0,0}, {1,1,1,0}, {0,0,1,0}, {0,0,0,0}},
        {{0,1,0,0}, {0,1,0,0}, {1,1,0,0}, {0,0,0,0}},
        {{1,0,0,0}, {1,1,1,0}, {0,0,0,0}, {0,0,0,0}},
        {{0,1,1,0}, {0,1,0,0}, {0,1,0,0}, {0,0,0,0}}
    }
};

// ============================================================
// COLLISION DETECTION
// ============================================================

/**
 * @brief   Check if piece can be placed at position
 */
static uint8_t can_place(int8_t px, int8_t py, uint8_t type, uint8_t rotation) {
    uint8_t row, col;
    int8_t gx, gy;
    
    for (row = 0; row < 4; row++) {
        for (col = 0; col < 4; col++) {
            if (pieces[type][rotation][row][col]) {
                gx = px + col;
                gy = py + row;
                
                // Check bounds
                if (gx < 0 || gx >= GRID_WIDTH) return 0;
                if (gy >= GRID_HEIGHT) return 0;
                
                // Check grid collision (only if on screen)
                if (gy >= 0 && game.grid[gy][gx]) return 0;
            }
        }
    }
    return 1;
}

// ============================================================
// PIECE MANAGEMENT
// ============================================================

/**
 * @brief   Lock current piece into grid
 */
static void lock_piece(void) {
    uint8_t row, col;
    int8_t gx, gy;
    
    for (row = 0; row < 4; row++) {
        for (col = 0; col < 4; col++) {
            if (pieces[game.current.type][game.current.rotation][row][col]) {
                gx = game.current.x + col;
                gy = game.current.y + row;
                
                if (gy >= 0 && gy < GRID_HEIGHT && gx >= 0 && gx < GRID_WIDTH) {
                    game.grid[gy][gx] = 1;
                }
            }
        }
    }
    game.needs_redraw = 1;
}

/**
 * @brief   Spawn new piece at top
 */
static void spawn_piece(void) {
    game.current.type = game.next_piece;
    game.current.rotation = 0;
    game.current.x = 3;  // Center
    game.current.y = 0;  // Start at top of visible area
    
    // Sync previous position immediately - prevents erasing stale old piece data
    game.prev_x = game.current.x;
    game.prev_y = game.current.y;
    game.prev_type = game.current.type;
    game.prev_rotation = game.current.rotation;
    
    // Generate next piece
    game.next_piece = rand8() % NUM_PIECES;
    
    // Check for game over
    if (!can_place(game.current.x, game.current.y, game.current.type, game.current.rotation)) {
        game.game_over = 1;
    }
    
    game.drop_timer = 0;
}

// ============================================================
// LINE CLEARING
// ============================================================

/**
 * @brief   Check and clear completed lines
 */
static void check_lines(void) {
    uint8_t row, col, full;
    uint8_t lines_cleared = 0;
    int8_t y, shift_row;
    
    for (row = 0; row < GRID_HEIGHT; row++) {
        full = 1;
        for (col = 0; col < GRID_WIDTH; col++) {
            if (!game.grid[row][col]) {
                full = 0;
                break;
            }
        }
        
        if (full) {
            lines_cleared++;
            
            // Shift all rows above down
            for (shift_row = row; shift_row > 0; shift_row--) {
                for (col = 0; col < GRID_WIDTH; col++) {
                    game.grid[shift_row][col] = game.grid[shift_row - 1][col];
                }
            }
            
            // Clear top row
            for (col = 0; col < GRID_WIDTH; col++) {
                game.grid[0][col] = 0;
            }
        }
    }
    
    if (lines_cleared > 0) {
        game.lines += lines_cleared;
        // Score: 1 line = 100, 2 = 300, 3 = 500, 4 = 800
        game.score += lines_cleared * 100 + (lines_cleared - 1) * 100;
        game.needs_redraw = 1;
    }
}

// ============================================================
// DISPLAY
// ============================================================

/**
 * @brief   Draw the playfield border
 */
static void draw_border(void) {
    uint8_t y;
    
    // Left and right walls
    for (y = 0; y < GRID_HEIGHT; y++) {
        set_bkg_tile_xy(GRID_OFFSET_X - 1, GRID_OFFSET_Y + y, TILE_WALL);
        set_bkg_tile_xy(GRID_OFFSET_X + GRID_WIDTH, GRID_OFFSET_Y + y, TILE_WALL);
    }
}

/**
 * @brief   Draw the grid contents
 */
static void draw_grid(void) {
    uint8_t row, col;
    
    for (row = 0; row < GRID_HEIGHT; row++) {
        for (col = 0; col < GRID_WIDTH; col++) {
            uint8_t tile = game.grid[row][col] ? TILE_BLOCK : TILE_EMPTY;
            set_bkg_tile_xy(GRID_OFFSET_X + col, GRID_OFFSET_Y + row, tile);
        }
    }
}

/**
 * @brief   Restore grid tile at position (erase piece tile)
 */
static void restore_grid_tile(int8_t gx, int8_t gy) {
    if (gy >= 0 && gy < GRID_HEIGHT && gx >= 0 && gx < GRID_WIDTH) {
        uint8_t tile = game.grid[gy][gx] ? TILE_BLOCK : TILE_EMPTY;
        set_bkg_tile_xy(GRID_OFFSET_X + gx, GRID_OFFSET_Y + gy, tile);
    }
}

/**
 * @brief   Draw current falling piece
 */
static void draw_piece(void) {
    uint8_t row, col;
    int8_t gx, gy;
    
    for (row = 0; row < 4; row++) {
        for (col = 0; col < 4; col++) {
            if (pieces[game.current.type][game.current.rotation][row][col]) {
                gx = game.current.x + col;
                gy = game.current.y + row;
                
                if (gy >= 0 && gy < GRID_HEIGHT && gx >= 0 && gx < GRID_WIDTH) {
                    set_bkg_tile_xy(GRID_OFFSET_X + gx, GRID_OFFSET_Y + gy, TILE_ACTIVE);
                }
            }
        }
    }
}

/**
 * @brief   Draw game over message
 */
static void draw_game_over(void) {
    // Simple "GAME OVER" in center area
    set_bkg_tile_xy(6, 9, TILE_WALL);
    set_bkg_tile_xy(7, 9, TILE_WALL);
    set_bkg_tile_xy(8, 9, TILE_WALL);
    set_bkg_tile_xy(9, 9, TILE_WALL);
    set_bkg_tile_xy(10, 9, TILE_WALL);
    set_bkg_tile_xy(11, 9, TILE_WALL);
    set_bkg_tile_xy(12, 9, TILE_WALL);
    set_bkg_tile_xy(13, 9, TILE_WALL);
}

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state
 */
void game_init(void) {
    uint8_t row, col;
    
    // Clear grid
    for (row = 0; row < GRID_HEIGHT; row++) {
        for (col = 0; col < GRID_WIDTH; col++) {
            game.grid[row][col] = 0;
        }
    }
    
    // Clear screen
    for (row = 0; row < 18; row++) {
        for (col = 0; col < 20; col++) {
            set_bkg_tile_xy(col, row, TILE_EMPTY);
        }
    }
    
    // Initialize state
    game.score = 0;
    game.lines = 0;
    game.game_over = 0;
    game.drop_timer = 0;
    game.drop_speed = DROP_SPEED_NORMAL;
    game.needs_redraw = 1;
    
    // First pieces
    game.next_piece = rand8() % NUM_PIECES;
    spawn_piece();
    
    // Initialize previous position tracking
    game.prev_x = game.current.x;
    game.prev_y = game.current.y;
    game.prev_type = game.current.type;
    game.prev_rotation = game.current.rotation;
    
    // Draw border
    draw_border();
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
    
    uint8_t pressed = curr_input & ~prev_input;
    
    // START: restart
    if (pressed & J_START) {
        if (game.game_over) {
            game_init();
            return;
        }
    }
    
    if (game.game_over) return;
    
    // Move left
    if (pressed & J_LEFT) {
        if (can_place(game.current.x - 1, game.current.y, 
                      game.current.type, game.current.rotation)) {
            game.current.x--;
        }
    }
    
    // Move right
    if (pressed & J_RIGHT) {
        if (can_place(game.current.x + 1, game.current.y,
                      game.current.type, game.current.rotation)) {
            game.current.x++;
        }
    }
    
    // Rotate
    if (pressed & J_A) {
        uint8_t new_rot = (game.current.rotation + 1) & 0x03;
        if (can_place(game.current.x, game.current.y,
                      game.current.type, new_rot)) {
            game.current.rotation = new_rot;
        }
    }
    
    // Fast drop (held)
    if (curr_input & J_DOWN) {
        game.drop_speed = DROP_SPEED_FAST;
    } else {
        game.drop_speed = DROP_SPEED_NORMAL;
    }
    
    // Seed RNG with input timing
    rand_seed ^= (uint8_t)(curr_input + game.drop_timer);
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Update game state
 */
void game_update(void) {
    if (game.game_over) return;
    
    game.drop_timer++;
    
    if (game.drop_timer >= game.drop_speed) {
        game.drop_timer = 0;
        
        // Try to move down
        if (can_place(game.current.x, game.current.y + 1,
                      game.current.type, game.current.rotation)) {
            game.current.y++;
        } else {
            // Can't move down - lock piece
            lock_piece();
            check_lines();
            spawn_piece();
        }
    }
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Render game - minimal tile updates to stay within VBlank
 */
void game_render(void) {
    uint8_t row, col;
    int8_t gx, gy;
    
    // Redraw entire grid when needed (after line clear or lock)
    if (game.needs_redraw) {
        draw_grid();
        game.needs_redraw = 0;
    }
    
    if (game.game_over) {
        draw_game_over();
        return;
    }
    
    // Only update tiles that changed between prev and current position
    // First, restore tiles that had old piece but won't have new piece
    for (row = 0; row < 4; row++) {
        for (col = 0; col < 4; col++) {
            if (pieces[game.prev_type][game.prev_rotation][row][col]) {
                gx = game.prev_x + col;
                gy = game.prev_y + row;
                
                // Check if this tile WON'T be covered by new piece
                int8_t local_x = gx - game.current.x;
                int8_t local_y = gy - game.current.y;
                
                uint8_t covered = 0;
                if (local_x >= 0 && local_x < 4 && local_y >= 0 && local_y < 4) {
                    if (pieces[game.current.type][game.current.rotation][local_y][local_x]) {
                        covered = 1;
                    }
                }
                
                if (!covered) {
                    restore_grid_tile(gx, gy);
                }
            }
        }
    }
    
    // Draw current piece
    draw_piece();
    
    // Update previous position
    game.prev_x = game.current.x;
    game.prev_y = game.current.y;
    game.prev_type = game.current.type;
    game.prev_rotation = game.current.rotation;
}
