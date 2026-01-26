/**
 * @file    main.c
 * @brief   Entry point for Memory Card Game
 * @game    memory
 * 
 * Initializes the game and runs the main loop.
 */

#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"

/**
 * @brief   Main entry point
 */
void main(void) {
    // Initialize tile data in VRAM
    sprites_init();
    
    // Initialize game state
    game_init();
    
    // Enable display
    SHOW_BKG;
    DISPLAY_ON;
    
    // Main game loop
    while(1) {
        wait_vbl_done();
        
        game_handle_input();
        game_update();
        game_render();
    }
}
