/**
 * @file    game.h
 * @brief   Game state and SRAM definitions for Clicker
 * @game    clicker
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// SRAM ADDRESSES
// ============================================================

// SRAM starts at 0xA000
#define SRAM_BASE       ((volatile uint8_t *)0xA000)

// Save data layout
#define SRAM_MAGIC      (SRAM_BASE + 0)     // Magic number (1 byte)
#define SRAM_HIGHSCORE_L (SRAM_BASE + 1)    // High score low byte
#define SRAM_HIGHSCORE_H (SRAM_BASE + 2)    // High score high byte

// Magic number to validate save
#define SAVE_MAGIC      0x42

// ============================================================
// GAME STATE
// ============================================================

typedef struct {
    uint16_t count;         // Current count
    uint16_t highscore;     // Loaded from SRAM
    uint8_t save_valid;     // Save data was valid on load
} GameState;

extern GameState game;
extern uint8_t prev_input;
extern uint8_t curr_input;

// ============================================================
// FUNCTIONS
// ============================================================

void game_init(void);
void game_handle_input(void);
void game_update(void);
void game_render(void);

void save_load(void);
void save_write(void);
void save_clear(void);

#endif
