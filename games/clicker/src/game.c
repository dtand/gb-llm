/**
 * @file    game.c
 * @brief   Counter logic and SRAM save/load for Clicker
 * @game    clicker
 * 
 * Demonstrates battery-backed SRAM for persistent saves.
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
// SAVE DATA FUNCTIONS
// ============================================================

/**
 * @brief   Load high score from SRAM
 * 
 * Validates save data using magic number before loading.
 */
void save_load(void) {
    ENABLE_RAM;
    
    // Check magic number
    if (*SRAM_MAGIC == SAVE_MAGIC) {
        // Valid save - load high score
        game.highscore = *SRAM_HIGHSCORE_L | (*SRAM_HIGHSCORE_H << 8);
        game.save_valid = 1;
    } else {
        // No valid save
        game.highscore = 0;
        game.save_valid = 0;
    }
    
    DISABLE_RAM;
}

/**
 * @brief   Write high score to SRAM
 * 
 * Writes magic number and 16-bit high score.
 */
void save_write(void) {
    ENABLE_RAM;
    
    *SRAM_MAGIC = SAVE_MAGIC;
    *SRAM_HIGHSCORE_L = game.highscore & 0xFF;
    *SRAM_HIGHSCORE_H = (game.highscore >> 8) & 0xFF;
    
    DISABLE_RAM;
}

/**
 * @brief   Clear saved data
 * 
 * Invalidates magic number to mark save as empty.
 */
void save_clear(void) {
    ENABLE_RAM;
    
    *SRAM_MAGIC = 0x00;
    *SRAM_HIGHSCORE_L = 0x00;
    *SRAM_HIGHSCORE_H = 0x00;
    
    DISABLE_RAM;
    
    game.highscore = 0;
    game.save_valid = 0;
}

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game and load save
 */
void game_init(void) {
    game.count = 0;
    save_load();
}

// ============================================================
// INPUT HANDLING
// ============================================================

/**
 * @brief   Handle input
 */
void game_handle_input(void) {
    prev_input = curr_input;
    curr_input = joypad();
    
    // A: increment count
    if ((curr_input & J_A) && !(prev_input & J_A)) {
        if (game.count < 9999) {
            game.count++;
        }
    }
    
    // B: reset current count
    if ((curr_input & J_B) && !(prev_input & J_B)) {
        game.count = 0;
    }
    
    // START: save high score
    if ((curr_input & J_START) && !(prev_input & J_START)) {
        save_write();
    }
    
    // SELECT: clear save data
    if ((curr_input & J_SELECT) && !(prev_input & J_SELECT)) {
        save_clear();
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Update game state
 */
void game_update(void) {
    // Update high score if beaten
    if (game.count > game.highscore) {
        game.highscore = game.count;
        save_write();   // Auto-save when high score beaten
    }
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Draw a number at tile position
 * 
 * @param x     Tile X position
 * @param y     Tile Y position
 * @param num   Number to display (0-9999)
 * @param digits Number of digits to show
 */
static void draw_number(uint8_t x, uint8_t y, uint16_t num, uint8_t digits) {
    uint8_t i;
    uint8_t digit;
    
    // Draw digits right-to-left
    for (i = 0; i < digits; i++) {
        digit = num % 10;
        set_bkg_tile_xy(x + digits - 1 - i, y, TILE_DIGIT_0 + digit);
        num /= 10;
    }
}

/**
 * @brief   Render score display
 */
void game_render(void) {
    // Row 6: "COUNT"
    set_bkg_tile_xy(6, 6, TILE_C);
    set_bkg_tile_xy(7, 6, TILE_O);
    set_bkg_tile_xy(8, 6, TILE_U);
    set_bkg_tile_xy(9, 6, TILE_N);
    set_bkg_tile_xy(10, 6, TILE_T);
    
    // Row 8: current count (4 digits)
    draw_number(7, 8, game.count, 4);
    
    // Row 11: "HIGH"
    set_bkg_tile_xy(7, 11, TILE_H);
    set_bkg_tile_xy(8, 11, TILE_I);
    set_bkg_tile_xy(9, 11, TILE_G);
    set_bkg_tile_xy(10, 11, TILE_H);
    
    // Row 13: high score (4 digits)
    draw_number(7, 13, game.highscore, 4);
}
