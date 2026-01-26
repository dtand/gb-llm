// Simon - Sprite and Tile Definitions
// Pattern memory game with 4 buttons and sound

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>

// ===========================================
// TILE INDICES - Background tiles
// ===========================================

#define TILE_EMPTY          0
#define TILE_BUTTON_TL      1   // Button top-left corner
#define TILE_BUTTON_TR      2   // Button top-right corner
#define TILE_BUTTON_BL      3   // Button bottom-left corner
#define TILE_BUTTON_BR      4   // Button bottom-right corner
#define TILE_BUTTON_LIT_TL  5   // Lit button top-left
#define TILE_BUTTON_LIT_TR  6   // Lit button top-right
#define TILE_BUTTON_LIT_BL  7   // Lit button bottom-left
#define TILE_BUTTON_LIT_BR  8   // Lit button bottom-right
#define TILE_CENTER         9   // Center piece

// HUD tiles
#define TILE_DIGIT_0        10
#define TILE_DIGIT_9        19
#define TILE_LETTER_S       20  // SCORE
#define TILE_LETTER_C       21
#define TILE_LETTER_O       22
#define TILE_LETTER_R       23
#define TILE_LETTER_E       24
#define TILE_LETTER_G       25  // GAME OVER
#define TILE_LETTER_A       26
#define TILE_LETTER_M       27
#define TILE_LETTER_V       28
#define TILE_LETTER_W       29  // WATCH
#define TILE_LETTER_T       30
#define TILE_LETTER_H       31
#define TILE_LETTER_P       32  // PLAY
#define TILE_LETTER_L       33
#define TILE_LETTER_Y       34
#define TILE_LETTER_I       35  // WIN
#define TILE_LETTER_N       36

// ===========================================
// BUTTON INDICES
// ===========================================

#define BTN_UP      0
#define BTN_RIGHT   1
#define BTN_DOWN    2
#define BTN_LEFT    3

// ===========================================
// SOUND FREQUENCIES (for each button)
// ===========================================

#define FREQ_UP     0x0500  // Higher pitch
#define FREQ_RIGHT  0x0580
#define FREQ_DOWN   0x0600
#define FREQ_LEFT   0x0680  // Lower pitch

// ===========================================
// GAME CONSTANTS
// ===========================================

#define MAX_SEQUENCE    32      // @tunable range:10-50 step:5 desc:"Max pattern length to win"
#define FLASH_FRAMES    20      // @tunable range:10-40 step:5 desc:"How long button stays lit in frames"
#define PAUSE_FRAMES    10      // @tunable range:5-20 step:5 desc:"Pause between flashes in frames"
#define INPUT_TIMEOUT   120     // @tunable range:60-180 step:30 desc:"Frames to wait for player input"

// ===========================================
// FUNCTION DECLARATIONS
// ===========================================

void sprites_init(void);
void play_tone(uint8_t button);
void stop_tone(void);

// Tile data arrays
extern const unsigned char button_tiles[];
extern const unsigned char hud_tiles[];

#endif
