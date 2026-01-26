/**
 * @file    game.c
 * @brief   Core game logic for Top-Down Adventure
 * @game    adventure
 * 
 * Demonstrates tile maps, 4-way movement, and NPC interaction.
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
// WORLD MAP
// ============================================================

// 20x18 tile map
// 0 = floor, 1 = wall, 2 = tree, 3 = path, 4 = door
const uint8_t world_map[MAP_HEIGHT][MAP_WIDTH] = {
    {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1},
    {1,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1},
    {1,0,0,1,1,1,1,4,1,1,0,0,0,0,0,0,2,0,0,1},
    {1,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1},
    {1,0,0,1,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,1},
    {1,0,0,1,1,1,1,1,1,1,0,0,0,0,0,1,1,1,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,0,1,0,1},
    {1,3,3,3,3,3,3,3,3,3,3,3,3,3,3,1,1,1,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1},
    {1,0,0,0,2,0,0,0,0,0,0,0,0,0,2,0,0,0,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1},
    {1,0,0,0,0,0,1,1,4,1,1,0,0,0,0,0,0,0,0,1},
    {1,0,2,0,0,0,1,0,0,0,1,0,0,0,0,0,2,0,0,1},
    {1,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,0,1},
    {1,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,1},
    {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}
};

// ============================================================
// TILE HELPERS
// ============================================================

/**
 * @brief   Get tile at position
 */
static uint8_t get_tile(uint8_t tx, uint8_t ty) {
    if (tx >= MAP_WIDTH || ty >= MAP_HEIGHT) return TILE_WALL;
    return world_map[ty][tx];
}

/**
 * @brief   Check if tile is solid (blocks movement)
 */
static uint8_t is_solid(uint8_t tile) {
    return (tile == TILE_WALL || tile == TILE_TREE);
}

/**
 * @brief   Check if position is blocked
 */
static uint8_t is_blocked(uint8_t tx, uint8_t ty) {
    // Check map bounds
    if (tx >= MAP_WIDTH || ty >= MAP_HEIGHT) return 1;
    
    // Check tile
    if (is_solid(get_tile(tx, ty))) return 1;
    
    // Check NPC
    if (game.npc.active && tx == game.npc.tile_x && ty == game.npc.tile_y) return 1;
    
    return 0;
}

// ============================================================
// MAP DRAWING
// ============================================================

/**
 * @brief   Draw the entire map
 */
static void draw_map(void) {
    uint8_t x, y;
    
    for (y = 0; y < MAP_HEIGHT; y++) {
        for (x = 0; x < MAP_WIDTH; x++) {
            uint8_t tile = world_map[y][x];
            uint8_t bg_tile;
            
            switch (tile) {
                case TILE_WALL:  bg_tile = BG_WALL; break;
                case TILE_TREE:  bg_tile = BG_TREE; break;
                case TILE_PATH:  bg_tile = BG_PATH; break;
                case TILE_DOOR:  bg_tile = BG_DOOR; break;
                default:         bg_tile = BG_FLOOR; break;
            }
            
            set_bkg_tile_xy(x, y, bg_tile);
        }
    }
}

// ============================================================
// DIALOG SYSTEM
// ============================================================

/**
 * @brief   Show dialog message using window layer
 */
static void show_dialog(void) {
    uint8_t x;
    
    // Fill window with solid dialog background
    for (x = 0; x < 20; x++) {
        set_win_tile_xy(x, 0, BG_DIALOG_BORDER);  // Top border
        set_win_tile_xy(x, 1, BG_DIALOG);         // Middle row 1
        set_win_tile_xy(x, 2, BG_DIALOG);         // Middle row 2
        set_win_tile_xy(x, 3, BG_DIALOG_BORDER);  // Bottom border
    }
    
    // Add left/right borders
    set_win_tile_xy(0, 1, BG_DIALOG_BORDER);
    set_win_tile_xy(0, 2, BG_DIALOG_BORDER);
    set_win_tile_xy(19, 1, BG_DIALOG_BORDER);
    set_win_tile_xy(19, 2, BG_DIALOG_BORDER);
    
    // Write "HELLO!" in the middle
    set_win_tile_xy(7, 1, BG_H);
    set_win_tile_xy(8, 1, BG_E);
    set_win_tile_xy(9, 1, BG_L);
    set_win_tile_xy(10, 1, BG_L);
    set_win_tile_xy(11, 1, BG_O);
    set_win_tile_xy(12, 1, BG_EXCLAIM);
    
    // Position window at bottom of screen
    move_win(7, 112);
    SHOW_WIN;
    
    game.dialog_active = 1;
    game.dialog_timer = 120;  // Show for 2 seconds
}

/**
 * @brief   Hide dialog
 */
static void hide_dialog(void) {
    HIDE_WIN;
    game.dialog_active = 0;
}

// ============================================================
// PLAYER MOVEMENT
// ============================================================

/**
 * @brief   Try to move player in direction
 */
static void try_move(uint8_t dir) {
    uint8_t new_x = game.player.tile_x;
    uint8_t new_y = game.player.tile_y;
    
    game.player.direction = dir;
    
    switch (dir) {
        case DIR_UP:    new_y--; break;
        case DIR_DOWN:  new_y++; break;
        case DIR_LEFT:  new_x--; break;
        case DIR_RIGHT: new_x++; break;
    }
    
    if (!is_blocked(new_x, new_y)) {
        game.player.tile_x = new_x;
        game.player.tile_y = new_y;
        game.player.move_timer = MOVE_DELAY;
    }
}

/**
 * @brief   Check if player is adjacent to NPC
 */
static uint8_t is_near_npc(void) {
    if (!game.npc.active) return 0;
    
    int8_t dx = (int8_t)game.player.tile_x - (int8_t)game.npc.tile_x;
    int8_t dy = (int8_t)game.player.tile_y - (int8_t)game.npc.tile_y;
    
    // Manhattan distance of 1
    if (dx < 0) dx = -dx;
    if (dy < 0) dy = -dy;
    
    return (dx + dy == 1);
}

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state
 */
void game_init(void) {
    // Setup player
    game.player.tile_x = 5;
    game.player.tile_y = 10;
    game.player.direction = DIR_DOWN;
    game.player.move_timer = 0;
    
    // Setup NPC in the village
    game.npc.tile_x = 8;
    game.npc.tile_y = 5;
    game.npc.active = 1;
    
    // Dialog off
    game.dialog_active = 0;
    game.dialog_timer = 0;
    
    // Draw map
    draw_map();
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
    
    // Dismiss dialog with any button
    if (game.dialog_active) {
        if (pressed & (J_A | J_B)) {
            hide_dialog();
        }
        return;
    }
    
    // Movement (with cooldown)
    if (game.player.move_timer == 0) {
        if (curr_input & J_UP) {
            try_move(DIR_UP);
        } else if (curr_input & J_DOWN) {
            try_move(DIR_DOWN);
        } else if (curr_input & J_LEFT) {
            try_move(DIR_LEFT);
        } else if (curr_input & J_RIGHT) {
            try_move(DIR_RIGHT);
        }
    }
    
    // Interact with NPC
    if (pressed & J_A) {
        if (is_near_npc()) {
            show_dialog();
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
    // Movement cooldown
    if (game.player.move_timer > 0) {
        game.player.move_timer--;
    }
    
    // Dialog timeout
    if (game.dialog_active && game.dialog_timer > 0) {
        game.dialog_timer--;
        if (game.dialog_timer == 0) {
            hide_dialog();
        }
    }
    
    // Update pixel positions from tile positions
    game.player.pixel_x = game.player.tile_x * 8 + 8;  // +8 for sprite offset
    game.player.pixel_y = game.player.tile_y * 8 + 16; // +16 for sprite offset
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Render game
 */
void game_render(void) {
    // Update player sprite position
    move_sprite(0, game.player.pixel_x, game.player.pixel_y);
    
    // Update NPC sprite position
    if (game.npc.active) {
        uint8_t npc_px = game.npc.tile_x * 8 + 8;
        uint8_t npc_py = game.npc.tile_y * 8 + 16;
        move_sprite(1, npc_px, npc_py);
    }
}
