/**
 * @file    game.c
 * @brief   Counter logic and SRAM save/load for Clicker
 * @game    clicker
 * 
 * Demonstrates battery-backed SRAM for persistent saves.
 */

#include <gb/gb.h>
#include <stdio.h>
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
 * @brief   Render score display using set_win_tiles
 */
void game_render(void) {
    static uint8_t last_count = 255;
    static uint16_t last_high = 65535;
    uint8_t digits[4];
    uint16_t temp;
    uint8_t i;
    
    // Only update if changed
    if (game.count != last_count || game.highscore != last_high) {
        last_count = game.count;
        last_high = game.highscore;
        
        // Draw current count digits at row 8
        temp = game.count;
        for (i = 0; i < 4; i++) {
            digits[3 - i] = temp % 10;
            temp /= 10;
        }
        for (i = 0; i < 4; i++) {
            set_bkg_tile_xy(7 + i, 8, digits[i]);
        }
        
        // Draw high score digits at row 13
        temp = game.highscore;
        for (i = 0; i < 4; i++) {
            digits[3 - i] = temp % 10;
            temp /= 10;
        }
        for (i = 0; i < 4; i++) {
            set_bkg_tile_xy(7 + i, 13, digits[i]);
        }
    }
}
