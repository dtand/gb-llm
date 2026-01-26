#include <gb/gb.h>
#include "game.h"
#include "sprites.h"

GameState game;

// Simple LCG random
static uint16_t random(void) {
    game.seed = game.seed * 1103515245 + 12345;
    return (game.seed >> 8) & 0x7FFF;
}

void draw_scene(void) {
    // Clear screen
    for (uint8_t y = 0; y < 18; y++) {
        for (uint8_t x = 0; x < 20; x++) {
            set_bkg_tile_xy(x, y, TILE_EMPTY);
        }
    }
    
    // Draw sky (empty, rows 0-7)
    
    // Draw dock on left side (rows 5-8)
    for (uint8_t y = 5; y < 9; y++) {
        for (uint8_t x = 0; x < 5; x++) {
            set_bkg_tile_xy(x, y, TILE_DOCK);
        }
    }
    
    // Draw grass/shore
    for (uint8_t x = 0; x < 5; x++) {
        set_bkg_tile_xy(x, 9, TILE_GRASS);
    }
    
    // Draw water (rows 9-17)
    for (uint8_t y = 9; y < 18; y++) {
        for (uint8_t x = 5; x < 20; x++) {
            set_bkg_tile_xy(x, y, TILE_WATER1);
        }
    }
    
    // Draw fisherman on dock (2x3 tiles)
    set_bkg_tile_xy(1, 5, TILE_MAN_TL);
    set_bkg_tile_xy(2, 5, TILE_MAN_TR);
    set_bkg_tile_xy(1, 6, TILE_MAN_ML);
    set_bkg_tile_xy(2, 6, TILE_MAN_MR);
    set_bkg_tile_xy(1, 7, TILE_MAN_BL);
    set_bkg_tile_xy(2, 7, TILE_MAN_BR);
    
    // Draw fishing rod extending from his hand
    set_bkg_tile_xy(3, 5, TILE_ROD);
    set_bkg_tile_xy(4, 6, TILE_ROD);
    set_bkg_tile_xy(5, 7, TILE_ROD);
}

void draw_hud(void) {
    // "FISH:" at top
    set_bkg_tile_xy(1, 1, TILE_F);
    set_bkg_tile_xy(2, 1, TILE_I);
    set_bkg_tile_xy(3, 1, TILE_S);
    set_bkg_tile_xy(4, 1, TILE_H);
    set_bkg_tile_xy(5, 1, TILE_COLON);
    
    // Fish count
    set_bkg_tile_xy(6, 1, TILE_NUM_0 + (game.fish_caught / 10) % 10);
    set_bkg_tile_xy(7, 1, TILE_NUM_0 + game.fish_caught % 10);
    
    // "MISS:" 
    set_bkg_tile_xy(12, 1, TILE_M);
    set_bkg_tile_xy(13, 1, TILE_I);
    set_bkg_tile_xy(14, 1, TILE_S);
    set_bkg_tile_xy(15, 1, TILE_S);
    set_bkg_tile_xy(16, 1, TILE_COLON);
    
    // Miss count
    set_bkg_tile_xy(17, 1, TILE_NUM_0 + (game.fish_missed / 10) % 10);
    set_bkg_tile_xy(18, 1, TILE_NUM_0 + game.fish_missed % 10);
}

void draw_title(void) {
    // Clear screen
    for (uint8_t y = 0; y < 18; y++) {
        for (uint8_t x = 0; x < 20; x++) {
            set_bkg_tile_xy(x, y, TILE_EMPTY);
        }
    }
    
    // "FISHING" centered
    set_bkg_tile_xy(6, 5, TILE_F);
    set_bkg_tile_xy(7, 5, TILE_I);
    set_bkg_tile_xy(8, 5, TILE_S);
    set_bkg_tile_xy(9, 5, TILE_H);
    set_bkg_tile_xy(10, 5, TILE_I);
    set_bkg_tile_xy(11, 5, TILE_N);
    set_bkg_tile_xy(12, 5, TILE_G);
    
    // Draw fish graphic
    set_bkg_tile_xy(8, 8, TILE_FISH_TL);
    set_bkg_tile_xy(9, 8, TILE_FISH_TR);
    set_bkg_tile_xy(8, 9, TILE_FISH_BL);
    set_bkg_tile_xy(9, 9, TILE_FISH_BR);
    
    // "PRESS A"
    set_bkg_tile_xy(6, 13, TILE_P);
    set_bkg_tile_xy(7, 13, TILE_R);
    set_bkg_tile_xy(8, 13, TILE_E);
    set_bkg_tile_xy(9, 13, TILE_S);
    set_bkg_tile_xy(10, 13, TILE_S);
    set_bkg_tile_xy(12, 13, TILE_A);
}

void draw_bobber(void) {
    uint8_t x = BOBBER_X;
    uint8_t y = game.bobber_y;
    
    set_bkg_tile_xy(x, y, TILE_BOBBER_TL);
    set_bkg_tile_xy(x + 1, y, TILE_BOBBER_TR);
    set_bkg_tile_xy(x, y + 1, TILE_BOBBER_BL);
    set_bkg_tile_xy(x + 1, y + 1, TILE_BOBBER_BR);
    
    // Draw line from rod to bobber
    set_bkg_tile_xy(6, 8, TILE_LINE);
    set_bkg_tile_xy(7, 9, TILE_LINE);
    if (y > BOBBER_Y_IDLE + 2) {
        set_bkg_tile_xy(8, 10, TILE_LINE);
        set_bkg_tile_xy(9, 11, TILE_LINE);
    }
}

void clear_bobber(void) {
    uint8_t x = BOBBER_X;
    uint8_t y = game.bobber_y;
    
    // Clear bobber tiles (restore water)
    set_bkg_tile_xy(x, y, (y >= 9) ? TILE_WATER1 : TILE_EMPTY);
    set_bkg_tile_xy(x + 1, y, (y >= 9) ? TILE_WATER1 : TILE_EMPTY);
    set_bkg_tile_xy(x, y + 1, (y + 1 >= 9) ? TILE_WATER1 : TILE_EMPTY);
    set_bkg_tile_xy(x + 1, y + 1, (y + 1 >= 9) ? TILE_WATER1 : TILE_EMPTY);
    
    // Clear line
    set_bkg_tile_xy(6, 8, TILE_EMPTY);
    set_bkg_tile_xy(7, 9, TILE_WATER1);
    set_bkg_tile_xy(8, 10, TILE_WATER1);
    set_bkg_tile_xy(9, 11, TILE_WATER1);
}

void draw_bite_indicator(void) {
    // Draw exclamation above bobber
    set_bkg_tile_xy(BOBBER_X, game.bobber_y - 2, TILE_EXCLAIM_T);
    set_bkg_tile_xy(BOBBER_X, game.bobber_y - 1, TILE_EXCLAIM_B);
}

void clear_bite_indicator(void) {
    set_bkg_tile_xy(BOBBER_X, game.bobber_y - 2, TILE_EMPTY);
    set_bkg_tile_xy(BOBBER_X, game.bobber_y - 1, TILE_EMPTY);
}

void draw_message(const char* msg, uint8_t len) {
    // Draw message at bottom center
    uint8_t x = (20 - len) / 2;
    for (uint8_t i = 0; i < len; i++) {
        uint8_t tile = TILE_EMPTY;
        switch (msg[i]) {
            case 'C': tile = TILE_C; break;
            case 'A': tile = TILE_A; break;
            case 'T': tile = TILE_T; break;
            case 'H': tile = TILE_H; break;
            case 'M': tile = TILE_M; break;
            case 'I': tile = TILE_I; break;
            case 'S': tile = TILE_S; break;
            case '!': tile = TILE_EXCLAIM; break;
            case ' ': tile = TILE_EMPTY; break;
        }
        set_bkg_tile_xy(x + i, 3, tile);
    }
}

void clear_message(void) {
    for (uint8_t x = 0; x < 20; x++) {
        set_bkg_tile_xy(x, 3, TILE_EMPTY);
    }
}

void animate_water(void) {
    game.water_timer++;
    if (game.water_timer >= 20) {
        game.water_timer = 0;
        game.water_frame = 1 - game.water_frame;
        
        uint8_t tile = game.water_frame ? TILE_WATER2 : TILE_WATER1;
        for (uint8_t y = 9; y < 18; y++) {
            for (uint8_t x = 5; x < 20; x++) {
                // Don't overwrite bobber area
                if (game.state >= STATE_WAITING && game.state <= STATE_REEL) {
                    if (x >= BOBBER_X && x <= BOBBER_X + 1 && 
                        y >= game.bobber_y && y <= game.bobber_y + 1) {
                        continue;
                    }
                }
                set_bkg_tile_xy(x, y, tile);
            }
        }
    }
}

void start_cast(void) {
    game.state = STATE_CAST;
    game.bobber_y = BOBBER_Y_IDLE;
    game.anim_timer = 0;
    draw_bobber();
}

void start_waiting(void) {
    game.state = STATE_WAITING;
    game.bobber_y = BOBBER_Y_WATER;
    // Random wait time between MIN_WAIT and MAX_WAIT frames
    game.wait_timer = MIN_WAIT + (random() % (MAX_WAIT - MIN_WAIT));
    clear_bobber();
    draw_bobber();
}

void game_init(void) {
    game.state = STATE_TITLE;
    game.fish_caught = 0;
    game.fish_missed = 0;
    game.seed = 54321;
    game.joypad_prev = 0;
    game.water_frame = 0;
    game.water_timer = 0;
    
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
                draw_scene();
                draw_hud();
                // Show "PRESS A" hint
                draw_message("CAST!", 5);
            }
            break;
            
        case STATE_IDLE:
            animate_water();
            if (joy_pressed & J_A) {
                clear_message();
                start_cast();
            }
            break;
            
        case STATE_CAST:
            // Animate bobber flying out
            game.anim_timer++;
            if (game.anim_timer % 4 == 0) {
                clear_bobber();
                game.bobber_y++;
                if (game.bobber_y >= BOBBER_Y_WATER) {
                    start_waiting();
                } else {
                    draw_bobber();
                }
            }
            break;
            
        case STATE_WAITING:
            animate_water();
            
            // Bobber bobbing animation
            game.anim_timer++;
            if (game.anim_timer % 30 == 0) {
                clear_bobber();
                game.bobber_y = BOBBER_Y_WATER + (game.anim_timer / 30) % 2;
                draw_bobber();
            }
            
            // Count down to bite
            if (game.wait_timer > 0) {
                game.wait_timer--;
            } else {
                // Fish bites!
                game.state = STATE_BITE;
                game.bite_timer = BITE_WINDOW;
                draw_bite_indicator();
            }
            break;
            
        case STATE_BITE:
            animate_water();
            
            // Flash the exclamation
            game.anim_timer++;
            if (game.anim_timer % 8 < 4) {
                draw_bite_indicator();
            } else {
                clear_bite_indicator();
            }
            
            // Check for player reaction
            if (joy_pressed & J_A) {
                // Caught it!
                clear_bite_indicator();
                game.state = STATE_CATCH;
                game.fish_caught++;
                draw_hud();
                draw_message("CATCH!", 6);
                game.anim_timer = 0;
            } else {
                // Count down bite window
                game.bite_timer--;
                if (game.bite_timer == 0) {
                    // Missed!
                    clear_bite_indicator();
                    game.state = STATE_MISS;
                    game.fish_missed++;
                    draw_hud();
                    draw_message("MISS!", 5);
                    game.anim_timer = 0;
                }
            }
            break;
            
        case STATE_CATCH:
            animate_water();
            game.anim_timer++;
            
            // Show fish being reeled in
            if (game.anim_timer == 20) {
                // Draw fish near bobber
                set_bkg_tile_xy(BOBBER_X - 1, game.bobber_y, TILE_FISH_TL);
                set_bkg_tile_xy(BOBBER_X, game.bobber_y, TILE_FISH_TR);
                set_bkg_tile_xy(BOBBER_X - 1, game.bobber_y + 1, TILE_FISH_BL);
                set_bkg_tile_xy(BOBBER_X, game.bobber_y + 1, TILE_FISH_BR);
            }
            
            if (game.anim_timer >= 90) {
                // Clear and return to idle
                clear_bobber();
                clear_message();
                // Clear fish
                set_bkg_tile_xy(BOBBER_X - 1, game.bobber_y, TILE_WATER1);
                set_bkg_tile_xy(BOBBER_X, game.bobber_y, TILE_WATER1);
                set_bkg_tile_xy(BOBBER_X - 1, game.bobber_y + 1, TILE_WATER1);
                set_bkg_tile_xy(BOBBER_X, game.bobber_y + 1, TILE_WATER1);
                draw_message("CAST!", 5);
                game.state = STATE_IDLE;
            }
            break;
            
        case STATE_MISS:
            animate_water();
            game.anim_timer++;
            
            if (game.anim_timer >= 60) {
                // Clear and return to idle
                clear_bobber();
                clear_message();
                draw_message("CAST!", 5);
                game.state = STATE_IDLE;
            }
            break;
    }
    
    game.joypad_prev = joy;
}
