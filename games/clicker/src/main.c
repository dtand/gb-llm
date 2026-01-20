/**
 * @file    main.c
 * @brief   Entry point for Clicker save demo
 * @game    clicker
 */

#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"

void main(void) {
    sprites_init();
    game_init();
    
    SHOW_BKG;
    DISPLAY_ON;
    
    while(1) {
        wait_vbl_done();
        game_handle_input();
        game_update();
        game_render();
    }
}
