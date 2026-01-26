#include <gb/gb.h>
#include "game.h"
#include "sprites.h"

GameState game;

// Simple LCG random
static uint16_t random(void) {
    game.seed = game.seed * 1103515245 + 12345;
    return (game.seed >> 8) & 0x7FFF;
}

// Draw a box frame
static void draw_box(uint8_t x, uint8_t y, uint8_t w, uint8_t h) {
    // Corners
    set_bkg_tile_xy(x, y, TILE_BOX_TL);
    set_bkg_tile_xy(x + w - 1, y, TILE_BOX_TR);
    set_bkg_tile_xy(x, y + h - 1, TILE_BOX_BL);
    set_bkg_tile_xy(x + w - 1, y + h - 1, TILE_BOX_BR);
    
    // Top and bottom edges
    for (uint8_t i = 1; i < w - 1; i++) {
        set_bkg_tile_xy(x + i, y, TILE_BOX_H);
        set_bkg_tile_xy(x + i, y + h - 1, TILE_BOX_H);
    }
    
    // Left and right edges
    for (uint8_t i = 1; i < h - 1; i++) {
        set_bkg_tile_xy(x, y + i, TILE_BOX_V);
        set_bkg_tile_xy(x + w - 1, y + i, TILE_BOX_V);
    }
    
    // Fill interior
    for (uint8_t iy = 1; iy < h - 1; iy++) {
        for (uint8_t ix = 1; ix < w - 1; ix++) {
            set_bkg_tile_xy(x + ix, y + iy, TILE_BOX_FILL);
        }
    }
}

void draw_title(void) {
    // Clear screen
    for (uint8_t y = 0; y < 18; y++) {
        for (uint8_t x = 0; x < 20; x++) {
            set_bkg_tile_xy(x, y, TILE_EMPTY);
        }
    }
    
    // "SLOTS" centered
    set_bkg_tile_xy(7, 5, TILE_S);
    set_bkg_tile_xy(8, 5, TILE_L);
    set_bkg_tile_xy(9, 5, TILE_O);
    set_bkg_tile_xy(10, 5, TILE_T);
    set_bkg_tile_xy(11, 5, TILE_S);
    
    // Draw sample symbols
    draw_symbol(3, 6, 8);   // 7
    draw_symbol(3, 9, 8);   // 7
    draw_symbol(3, 12, 8);  // 7
    
    // "PRESS A"
    set_bkg_tile_xy(6, 13, TILE_P);
    set_bkg_tile_xy(7, 13, TILE_R);
    set_bkg_tile_xy(8, 13, TILE_E);
    set_bkg_tile_xy(9, 13, TILE_S);
    set_bkg_tile_xy(10, 13, TILE_S);
    set_bkg_tile_xy(12, 13, TILE_A);
}

void draw_game_screen(void) {
    // Clear screen
    for (uint8_t y = 0; y < 18; y++) {
        for (uint8_t x = 0; x < 20; x++) {
            set_bkg_tile_xy(x, y, TILE_EMPTY);
        }
    }
    
    // Draw three reel boxes
    draw_box(REEL1_X - 1, REELS_Y - 1, 4, 4);
    draw_box(REEL2_X - 1, REELS_Y - 1, 4, 4);
    draw_box(REEL3_X - 1, REELS_Y - 1, 4, 4);
    
    // "COINS:" at top
    set_bkg_tile_xy(1, 1, TILE_C);
    set_bkg_tile_xy(2, 1, TILE_O);
    set_bkg_tile_xy(3, 1, TILE_I);
    set_bkg_tile_xy(4, 1, TILE_N);
    set_bkg_tile_xy(5, 1, TILE_S);
    set_bkg_tile_xy(6, 1, TILE_COLON);
    
    // "BET:10" at top right
    set_bkg_tile_xy(12, 1, TILE_B);
    set_bkg_tile_xy(13, 1, TILE_E);
    set_bkg_tile_xy(14, 1, TILE_T);
    set_bkg_tile_xy(15, 1, TILE_COLON);
    set_bkg_tile_xy(16, 1, TILE_NUM_1);
    set_bkg_tile_xy(17, 1, TILE_NUM_0);
    
    // "PRESS A" hint at bottom
    set_bkg_tile_xy(6, 15, TILE_P);
    set_bkg_tile_xy(7, 15, TILE_R);
    set_bkg_tile_xy(8, 15, TILE_E);
    set_bkg_tile_xy(9, 15, TILE_S);
    set_bkg_tile_xy(10, 15, TILE_S);
    set_bkg_tile_xy(12, 15, TILE_A);
    
    draw_coins();
    draw_reels();
}

void draw_reels(void) {
    draw_symbol(game.reel1, REEL1_X, REELS_Y);
    draw_symbol(game.reel2, REEL2_X, REELS_Y);
    draw_symbol(game.reel3, REEL3_X, REELS_Y);
}

void draw_coins(void) {
    uint16_t c = game.coins;
    
    // Draw up to 4 digits (left to right: thousands, hundreds, tens, ones)
    set_bkg_tile_xy(7, 1, TILE_NUM_0 + (c / 1000) % 10);
    set_bkg_tile_xy(8, 1, TILE_NUM_0 + (c / 100) % 10);
    set_bkg_tile_xy(9, 1, TILE_NUM_0 + (c / 10) % 10);
    set_bkg_tile_xy(10, 1, TILE_NUM_0 + c % 10);
}

void draw_win(uint16_t amount) {
    // "WIN:" on row 13
    set_bkg_tile_xy(6, 13, TILE_W);
    set_bkg_tile_xy(7, 13, TILE_I);
    set_bkg_tile_xy(8, 13, TILE_N);
    set_bkg_tile_xy(9, 13, TILE_COLON);
    
    // Amount
    set_bkg_tile_xy(10, 13, TILE_NUM_0 + (amount / 100) % 10);
    set_bkg_tile_xy(11, 13, TILE_NUM_0 + (amount / 10) % 10);
    set_bkg_tile_xy(12, 13, TILE_NUM_0 + amount % 10);
    set_bkg_tile_xy(13, 13, TILE_EXCLAIM);
}

void clear_win(void) {
    // Clear win line
    for (uint8_t x = 5; x < 15; x++) {
        set_bkg_tile_xy(x, 13, TILE_EMPTY);
    }
}

void draw_gameover(void) {
    // Clear middle area
    for (uint8_t x = 4; x < 16; x++) {
        for (uint8_t y = 12; y < 15; y++) {
            set_bkg_tile_xy(x, y, TILE_EMPTY);
        }
    }
    
    // "NO COINS!"
    set_bkg_tile_xy(5, 13, TILE_N);
    set_bkg_tile_xy(6, 13, TILE_O);
    set_bkg_tile_xy(8, 13, TILE_C);
    set_bkg_tile_xy(9, 13, TILE_O);
    set_bkg_tile_xy(10, 13, TILE_I);
    set_bkg_tile_xy(11, 13, TILE_N);
    set_bkg_tile_xy(12, 13, TILE_S);
    set_bkg_tile_xy(13, 13, TILE_EXCLAIM);
}

void start_spin(void) {
    // Deduct bet
    if (game.coins >= BET_AMOUNT) {
        game.coins -= BET_AMOUNT;
        draw_coins();
        clear_win();
        
        // Initialize spin state
        game.reel1_spinning = 1;
        game.reel2_spinning = 1;
        game.reel3_spinning = 1;
        game.spin_count1 = MIN_SPINS + (random() % 10);
        game.spin_count2 = game.spin_count1 + STOP_DELAY;
        game.spin_count3 = game.spin_count2 + STOP_DELAY;
        game.spin_timer = 0;
        game.state = STATE_SPINNING;
    }
}

uint16_t calculate_payout(void) {
    // Three of a kind - jackpot payout
    if (game.reel1 == game.reel2 && game.reel2 == game.reel3) {
        switch (game.reel1) {
            case 0: return PAYOUT_CHERRY * 3;   // Cherry = 15
            case 1: return PAYOUT_BELL * 3;     // Bell = 30
            case 2: return PAYOUT_BAR * 3;      // Bar = 60
            case 3: return PAYOUT_SEVEN * 3;    // Seven = 150
            case 4: return PAYOUT_STAR * 3;     // Star = 300
        }
    }
    
    // Two of a kind (first two)
    if (game.reel1 == game.reel2) {
        switch (game.reel1) {
            case 0: return PAYOUT_CHERRY;
            case 1: return PAYOUT_BELL;
            case 2: return PAYOUT_BAR;
            case 3: return PAYOUT_SEVEN;
            case 4: return PAYOUT_STAR;
        }
    }
    
    // Any cherry gives small payout
    if (game.reel1 == 0 || game.reel2 == 0 || game.reel3 == 0) {
        return 2;  // 2 coins for any cherry
    }
    
    return 0;  // No win
}

void game_init(void) {
    game.state = STATE_TITLE;
    game.coins = START_COINS;
    game.seed = 12345;
    game.joypad_prev = 0;
    
    // Initialize reels to random symbols
    game.reel1 = random() % NUM_SYMBOLS;
    game.reel2 = random() % NUM_SYMBOLS;
    game.reel3 = random() % NUM_SYMBOLS;
    
    draw_title();
}

void game_update(void) {
    uint8_t joy = joypad();
    uint8_t joy_pressed = joy & ~game.joypad_prev;
    
    // Increment seed for randomness
    game.seed++;
    
    switch (game.state) {
        case STATE_TITLE:
            if (joy_pressed & J_A) {
                game.state = STATE_IDLE;
                draw_game_screen();
            }
            break;
            
        case STATE_IDLE:
            if (joy_pressed & J_A) {
                if (game.coins >= BET_AMOUNT) {
                    start_spin();
                } else {
                    game.state = STATE_GAMEOVER;
                    draw_gameover();
                }
            }
            break;
            
        case STATE_SPINNING:
            game.spin_timer++;
            
            if (game.spin_timer >= SPIN_FRAMES) {
                game.spin_timer = 0;
                
                // Spin each active reel
                if (game.reel1_spinning) {
                    game.reel1 = (game.reel1 + 1) % NUM_SYMBOLS;
                    game.spin_count1--;
                    if (game.spin_count1 == 0) {
                        game.reel1_spinning = 0;
                        // Final symbol is random
                        game.reel1 = random() % NUM_SYMBOLS;
                    }
                }
                
                if (game.reel2_spinning) {
                    game.reel2 = (game.reel2 + 1) % NUM_SYMBOLS;
                    game.spin_count2--;
                    if (game.spin_count2 == 0) {
                        game.reel2_spinning = 0;
                        game.reel2 = random() % NUM_SYMBOLS;
                    }
                }
                
                if (game.reel3_spinning) {
                    game.reel3 = (game.reel3 + 1) % NUM_SYMBOLS;
                    game.spin_count3--;
                    if (game.spin_count3 == 0) {
                        game.reel3_spinning = 0;
                        game.reel3 = random() % NUM_SYMBOLS;
                    }
                }
                
                draw_reels();
                
                // Check if all stopped
                if (!game.reel1_spinning && !game.reel2_spinning && !game.reel3_spinning) {
                    game.state = STATE_RESULT;
                    game.result_timer = 30;  // Brief pause before showing result
                }
            }
            break;
            
        case STATE_RESULT:
            if (game.result_timer > 0) {
                game.result_timer--;
            } else {
                // Calculate and award winnings
                game.last_win = calculate_payout();
                if (game.last_win > 0) {
                    game.coins += game.last_win;
                    draw_coins();
                    draw_win(game.last_win);
                }
                game.state = STATE_IDLE;
            }
            break;
            
        case STATE_GAMEOVER:
            // Press START to restart
            if (joy_pressed & J_START) {
                game.coins = START_COINS;
                game.state = STATE_IDLE;
                draw_game_screen();
            }
            break;
    }
    
    game.joypad_prev = joy;
}
