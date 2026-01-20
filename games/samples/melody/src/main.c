/**
 * @file    main.c
 * @brief   Entry point for Melody music demo
 * @game    melody
 */

#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"

void main(void) {
    sprites_init();
    game_init();
    
    SHOW_SPRITES;
    DISPLAY_ON;
    
    while(1) {
        wait_vbl_done();
        game_handle_input();
        game_update();
        game_render();
    }
}
