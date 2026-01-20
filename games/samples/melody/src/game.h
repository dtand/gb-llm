/**
 * @file    game.h
 * @brief   Music state and note definitions for Melody
 * @game    melody
 */

#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// SOUND REGISTER ADDRESSES
// ============================================================

// Channel 1 (Square with sweep)
#define NR10_REG    (*((volatile uint8_t *)0xFF10))
#define NR11_REG    (*((volatile uint8_t *)0xFF11))
#define NR12_REG    (*((volatile uint8_t *)0xFF12))
#define NR13_REG    (*((volatile uint8_t *)0xFF13))
#define NR14_REG    (*((volatile uint8_t *)0xFF14))

// Master control
#define NR50_REG    (*((volatile uint8_t *)0xFF24))
#define NR51_REG    (*((volatile uint8_t *)0xFF25))
#define NR52_REG    (*((volatile uint8_t *)0xFF26))

// ============================================================
// NOTE FREQUENCIES (11-bit values for GB)
// ============================================================
// Formula: freq_reg = 2048 - (131072 / frequency_hz)

#define NOTE_C4     1046    // ~262 Hz
#define NOTE_D4     1178    // ~294 Hz
#define NOTE_E4     1294    // ~330 Hz
#define NOTE_F4     1346    // ~349 Hz
#define NOTE_G4     1430    // ~392 Hz
#define NOTE_A4     1542    // ~440 Hz
#define NOTE_B4     1622    // ~494 Hz
#define NOTE_C5     1710    // ~523 Hz
#define NOTE_REST   0       // Silence

// ============================================================
// GAME STATE
// ============================================================

#define DEFAULT_TEMPO   15      // Frames per note
#define MIN_TEMPO       5
#define MAX_TEMPO       30

typedef struct {
    uint8_t playing;        // Music is playing
    uint8_t tempo;          // Frames per note
    uint8_t frame_count;    // Frames since last note
    uint8_t note_index;     // Current note in sequence
    uint8_t visual_pulse;   // Visual indicator size (0-3)
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

void sound_init(void);
void sound_play_note(uint16_t freq);
void sound_stop(void);

#endif
