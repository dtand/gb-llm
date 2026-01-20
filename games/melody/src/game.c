/**
 * @file    game.c
 * @brief   Music sequencer and sound control for Melody
 * @game    melody
 * 
 * Demonstrates Game Boy sound register usage for music.
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
// MELODY SEQUENCE
// ============================================================

// Simple melody: "Twinkle Twinkle Little Star" fragment
static const uint16_t melody[] = {
    NOTE_C4, NOTE_C4, NOTE_G4, NOTE_G4,
    NOTE_A4, NOTE_A4, NOTE_G4, NOTE_REST,
    NOTE_F4, NOTE_F4, NOTE_E4, NOTE_E4,
    NOTE_D4, NOTE_D4, NOTE_C4, NOTE_REST
};

#define MELODY_LENGTH   (sizeof(melody) / sizeof(melody[0]))

// ============================================================
// SOUND FUNCTIONS
// ============================================================

/**
 * @brief   Initialize sound hardware
 * 
 * Enables master sound and configures channel 1.
 */
void sound_init(void) {
    // Enable sound (bit 7 of NR52)
    NR52_REG = 0x80;
    
    // Max volume, both speakers
    NR50_REG = 0x77;
    
    // Enable channel 1 on both left and right
    NR51_REG = 0x11;
    
    // Channel 1: no sweep
    NR10_REG = 0x00;
    
    // Channel 1: 50% duty cycle
    NR11_REG = 0x80;
    
    // Channel 1: volume envelope (start at max, no change)
    NR12_REG = 0xF0;
}

/**
 * @brief   Play a note on channel 1
 * 
 * @param freq  11-bit frequency register value (0 = rest/silence)
 */
void sound_play_note(uint16_t freq) {
    if (freq == NOTE_REST) {
        // Silence: set volume to 0
        NR12_REG = 0x00;
        NR14_REG = 0x80;    // Trigger to apply volume change
        return;
    }
    
    // Set volume envelope (restart at max volume)
    NR12_REG = 0xF0;
    
    // Set frequency (11 bits split across NR13 and NR14)
    NR13_REG = freq & 0xFF;             // Low 8 bits
    NR14_REG = 0x80 | ((freq >> 8) & 0x07);  // Trigger + high 3 bits
}

/**
 * @brief   Stop all sound
 */
void sound_stop(void) {
    NR12_REG = 0x00;    // Volume to 0
    NR14_REG = 0x80;    // Trigger to apply
}

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game and sound
 */
void game_init(void) {
    game.playing = 1;
    game.tempo = DEFAULT_TEMPO;
    game.frame_count = 0;
    game.note_index = 0;
    game.visual_pulse = 0;
    
    sound_init();
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
    
    // A: toggle play/pause
    if ((curr_input & J_A) && !(prev_input & J_A)) {
        game.playing = !game.playing;
        if (!game.playing) {
            sound_stop();
        }
    }
    
    // START: reset
    if ((curr_input & J_START) && !(prev_input & J_START)) {
        game_init();
    }
    
    // D-pad up/down: change tempo
    if ((curr_input & J_UP) && !(prev_input & J_UP)) {
        if (game.tempo > MIN_TEMPO) {
            game.tempo--;
        }
    }
    if ((curr_input & J_DOWN) && !(prev_input & J_DOWN)) {
        if (game.tempo < MAX_TEMPO) {
            game.tempo++;
        }
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Update music sequencer
 */
void game_update(void) {
    if (!game.playing) return;
    
    game.frame_count++;
    
    // Time for next note?
    if (game.frame_count >= game.tempo) {
        game.frame_count = 0;
        
        // Play current note
        sound_play_note(melody[game.note_index]);
        
        // Update visual pulse (larger for non-rest notes)
        if (melody[game.note_index] != NOTE_REST) {
            game.visual_pulse = 3;
        }
        
        // Advance to next note
        game.note_index++;
        if (game.note_index >= MELODY_LENGTH) {
            game.note_index = 0;
        }
    }
    
    // Decay visual pulse
    if (game.visual_pulse > 0 && (game.frame_count & 0x03) == 0) {
        game.visual_pulse--;
    }
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Render visual indicator
 */
void game_render(void) {
    // Update sprite tile based on pulse level
    set_sprite_tile(SPRITE_INDICATOR, TILE_PULSE_0 + game.visual_pulse);
    
    // Center on screen
    move_sprite(SPRITE_INDICATOR, 84, 80);
}
