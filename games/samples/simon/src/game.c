// Simon - Game Logic Implementation

#include <gb/gb.h>
#include <rand.h>
#include "game.h"
#include "sprites.h"

// Global game state
GameState game;

// Button tile positions (x, y for each button's top-left)
static const uint8_t button_pos[4][2] = {
    {BTN_UP_X, BTN_UP_Y},       // UP
    {BTN_RIGHT_X, BTN_RIGHT_Y}, // RIGHT
    {BTN_DOWN_X, BTN_DOWN_Y},   // DOWN
    {BTN_LEFT_X, BTN_LEFT_Y}    // LEFT
};

// ===========================================
// INITIALIZATION
// ===========================================

void game_init(void) {
    uint8_t i, j;
    
    // Clear sequence
    for (i = 0; i < MAX_SEQUENCE; i++) {
        game.sequence[i] = 0;
    }
    
    game.sequence_length = 0;
    game.current_step = 0;
    game.flash_timer = 0;
    game.pause_timer = 0;
    game.input_timer = 0;
    game.lit_button = 0xFF;  // None lit
    game.last_keys = 0;
    game.score = 0;
    game.state = STATE_TITLE;
    
    // Initialize random seed
    initrand(DIV_REG);
    
    // Clear entire background to remove garbage tiles
    for (j = 0; j < 18; j++) {
        for (i = 0; i < 20; i++) {
            set_bkg_tile_xy(i, j, TILE_EMPTY);
        }
    }
    
    // Draw initial screen
    draw_all_buttons();
    draw_hud();
    draw_message(MSG_NONE);
    
    SHOW_BKG;
}

// ===========================================
// BUTTON DRAWING
// ===========================================

void draw_button(uint8_t button, uint8_t lit) {
    uint8_t x = button_pos[button][0];
    uint8_t y = button_pos[button][1];
    uint8_t tl, tr, bl, br;
    
    if (lit) {
        tl = TILE_BUTTON_LIT_TL;
        tr = TILE_BUTTON_LIT_TR;
        bl = TILE_BUTTON_LIT_BL;
        br = TILE_BUTTON_LIT_BR;
    } else {
        tl = TILE_BUTTON_TL;
        tr = TILE_BUTTON_TR;
        bl = TILE_BUTTON_BL;
        br = TILE_BUTTON_BR;
    }
    
    // Draw 4x4 button (using 2x2 arrangement of corner tiles repeated)
    // Top row
    set_bkg_tile_xy(x, y, tl);
    set_bkg_tile_xy(x + 1, y, tl);
    set_bkg_tile_xy(x + 2, y, tr);
    set_bkg_tile_xy(x + 3, y, tr);
    // Second row
    set_bkg_tile_xy(x, y + 1, tl);
    set_bkg_tile_xy(x + 1, y + 1, tl);
    set_bkg_tile_xy(x + 2, y + 1, tr);
    set_bkg_tile_xy(x + 3, y + 1, tr);
    // Third row
    set_bkg_tile_xy(x, y + 2, bl);
    set_bkg_tile_xy(x + 1, y + 2, bl);
    set_bkg_tile_xy(x + 2, y + 2, br);
    set_bkg_tile_xy(x + 3, y + 2, br);
    // Bottom row
    set_bkg_tile_xy(x, y + 3, bl);
    set_bkg_tile_xy(x + 1, y + 3, bl);
    set_bkg_tile_xy(x + 2, y + 3, br);
    set_bkg_tile_xy(x + 3, y + 3, br);
}

void draw_all_buttons(void) {
    draw_button(BTN_UP, 0);
    draw_button(BTN_RIGHT, 0);
    draw_button(BTN_DOWN, 0);
    draw_button(BTN_LEFT, 0);
    
    // Draw center
    set_bkg_tile_xy(9, 8, TILE_CENTER);
    set_bkg_tile_xy(10, 8, TILE_CENTER);
    set_bkg_tile_xy(9, 9, TILE_CENTER);
    set_bkg_tile_xy(10, 9, TILE_CENTER);
}

void light_button(uint8_t button) {
    draw_button(button, 1);
    play_tone(button);
    game.lit_button = button;
}

void unlight_button(uint8_t button) {
    draw_button(button, 0);
    stop_tone();
    game.lit_button = 0xFF;
}

// ===========================================
// PATTERN MANAGEMENT
// ===========================================

void add_to_sequence(void) {
    if (game.sequence_length < MAX_SEQUENCE) {
        game.sequence[game.sequence_length] = rand() & 0x03;  // 0-3
        game.sequence_length++;
    }
}

void start_show_pattern(void) {
    game.current_step = 0;
    game.flash_timer = 0;
    game.pause_timer = PAUSE_FRAMES;  // Start with a pause
    game.state = STATE_SHOW_PATTERN;
    draw_message(MSG_WATCH);
}

// ===========================================
// HUD DRAWING
// ===========================================

void draw_number(uint8_t x, uint8_t y, uint8_t num, uint8_t digits) {
    uint8_t i;
    uint8_t divisor = 1;
    
    for (i = 1; i < digits; i++) {
        divisor *= 10;
    }
    
    for (i = 0; i < digits; i++) {
        set_bkg_tile_xy(x + i, y, TILE_DIGIT_0 + ((num / divisor) % 10));
        divisor /= 10;
    }
}

void draw_hud(void) {
    // SCORE at top
    set_bkg_tile_xy(1, 0, TILE_LETTER_S);
    set_bkg_tile_xy(2, 0, TILE_LETTER_C);
    set_bkg_tile_xy(3, 0, TILE_LETTER_O);
    set_bkg_tile_xy(4, 0, TILE_LETTER_R);
    set_bkg_tile_xy(5, 0, TILE_LETTER_E);
    draw_number(7, 0, game.score, 2);
}

void draw_message(uint8_t msg) {
    // Clear message area (row 16-17)
    uint8_t i;
    for (i = 0; i < 20; i++) {
        set_bkg_tile_xy(i, 16, TILE_EMPTY);
        set_bkg_tile_xy(i, 17, TILE_EMPTY);
    }
    
    switch (msg) {
        case MSG_WATCH:
            // "WATCH"
            set_bkg_tile_xy(7, 16, TILE_LETTER_W);
            set_bkg_tile_xy(8, 16, TILE_LETTER_A);
            set_bkg_tile_xy(9, 16, TILE_LETTER_T);
            set_bkg_tile_xy(10, 16, TILE_LETTER_C);
            set_bkg_tile_xy(11, 16, TILE_LETTER_H);
            break;
            
        case MSG_PLAY:
            // "PLAY"
            set_bkg_tile_xy(8, 16, TILE_LETTER_P);
            set_bkg_tile_xy(9, 16, TILE_LETTER_L);
            set_bkg_tile_xy(10, 16, TILE_LETTER_A);
            set_bkg_tile_xy(11, 16, TILE_LETTER_Y);
            break;
            
        case MSG_GAME_OVER:
            // "GAME OVER"
            set_bkg_tile_xy(5, 16, TILE_LETTER_G);
            set_bkg_tile_xy(6, 16, TILE_LETTER_A);
            set_bkg_tile_xy(7, 16, TILE_LETTER_M);
            set_bkg_tile_xy(8, 16, TILE_LETTER_E);
            set_bkg_tile_xy(10, 16, TILE_LETTER_O);
            set_bkg_tile_xy(11, 16, TILE_LETTER_V);
            set_bkg_tile_xy(12, 16, TILE_LETTER_E);
            set_bkg_tile_xy(13, 16, TILE_LETTER_R);
            break;
            
        case MSG_WIN:
            // "WIN"
            set_bkg_tile_xy(8, 16, TILE_LETTER_W);
            set_bkg_tile_xy(9, 16, TILE_LETTER_I);
            set_bkg_tile_xy(10, 16, TILE_LETTER_N);
            break;
    }
}

// ===========================================
// INPUT HANDLING
// ===========================================

void game_handle_input(void) {
    uint8_t keys = joypad();
    uint8_t pressed = keys & ~game.last_keys;  // Newly pressed this frame
    
    if (game.state == STATE_TITLE) {
        if (pressed & J_START) {
            // Start new game
            game.score = 0;
            game.sequence_length = 0;
            add_to_sequence();
            start_show_pattern();
        }
    }
    else if (game.state == STATE_PLAYER_INPUT) {
        uint8_t input_button = 0xFF;
        
        // Check D-pad input
        if (pressed & J_UP) input_button = BTN_UP;
        else if (pressed & J_RIGHT) input_button = BTN_RIGHT;
        else if (pressed & J_DOWN) input_button = BTN_DOWN;
        else if (pressed & J_LEFT) input_button = BTN_LEFT;
        
        if (input_button != 0xFF) {
            // Player pressed a button
            light_button(input_button);
            game.flash_timer = FLASH_FRAMES;
            game.input_timer = INPUT_TIMEOUT;  // Reset timeout
            
            // Check if correct
            if (input_button == game.sequence[game.current_step]) {
                game.current_step++;
                
                // Check if completed the sequence
                if (game.current_step >= game.sequence_length) {
                    game.score = game.sequence_length;
                    draw_hud();
                    
                    // Check for win
                    if (game.sequence_length >= MAX_SEQUENCE) {
                        game.state = STATE_WIN;
                        draw_message(MSG_WIN);
                    } else {
                        game.state = STATE_CORRECT;
                        game.pause_timer = 60;  // 1 second pause before next round
                    }
                }
            } else {
                // Wrong button!
                game.state = STATE_GAME_OVER;
                draw_message(MSG_GAME_OVER);
                if (game.score > game.high_score) {
                    game.high_score = game.score;
                }
            }
        }
    }
    else if (game.state == STATE_GAME_OVER || game.state == STATE_WIN) {
        if (pressed & J_START) {
            // Restart
            game.score = 0;
            game.sequence_length = 0;
            draw_all_buttons();
            add_to_sequence();
            start_show_pattern();
            draw_hud();
        }
    }
    
    game.last_keys = keys;
}

// ===========================================
// GAME UPDATE
// ===========================================

void game_update(void) {
    switch (game.state) {
        case STATE_SHOW_PATTERN:
            // Handle pause between flashes
            if (game.pause_timer > 0) {
                game.pause_timer--;
                break;
            }
            
            // Handle button flash
            if (game.flash_timer > 0) {
                game.flash_timer--;
                if (game.flash_timer == 0) {
                    // Turn off the button
                    unlight_button(game.sequence[game.current_step]);
                    game.current_step++;
                    game.pause_timer = PAUSE_FRAMES;
                }
            } else {
                // Start next flash
                if (game.current_step < game.sequence_length) {
                    light_button(game.sequence[game.current_step]);
                    game.flash_timer = FLASH_FRAMES;
                } else {
                    // Done showing pattern
                    game.current_step = 0;
                    game.input_timer = INPUT_TIMEOUT;
                    game.state = STATE_PLAYER_INPUT;
                    draw_message(MSG_PLAY);
                }
            }
            break;
            
        case STATE_PLAYER_INPUT:
            // Handle button release after flash
            if (game.flash_timer > 0) {
                game.flash_timer--;
                if (game.flash_timer == 0 && game.lit_button != 0xFF) {
                    unlight_button(game.lit_button);
                }
            }
            
            // Handle input timeout
            if (game.input_timer > 0) {
                game.input_timer--;
                if (game.input_timer == 0) {
                    // Timeout - game over
                    game.state = STATE_GAME_OVER;
                    draw_message(MSG_GAME_OVER);
                    if (game.score > game.high_score) {
                        game.high_score = game.score;
                    }
                }
            }
            break;
            
        case STATE_CORRECT:
            // Handle button release after player's final input
            if (game.flash_timer > 0) {
                game.flash_timer--;
                if (game.flash_timer == 0 && game.lit_button != 0xFF) {
                    unlight_button(game.lit_button);
                }
            }
            
            // Brief pause after completing a sequence (only count down after button is off)
            if (game.lit_button == 0xFF && game.pause_timer > 0) {
                game.pause_timer--;
            } else if (game.lit_button == 0xFF && game.pause_timer == 0) {
                // Add to sequence and show again
                add_to_sequence();
                start_show_pattern();
            }
            break;
            
        case STATE_GAME_OVER:
        case STATE_WIN:
            // Handle any lingering lit button
            if (game.flash_timer > 0) {
                game.flash_timer--;
                if (game.flash_timer == 0 && game.lit_button != 0xFF) {
                    unlight_button(game.lit_button);
                }
            }
            break;
    }
}

// ===========================================
// DRAW (called every frame)
// ===========================================

void game_draw(void) {
    // Most drawing is done in response to events
    // This is just for any per-frame updates
}
