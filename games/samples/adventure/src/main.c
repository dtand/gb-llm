/**
 * @file    main.c
 * @brief   Entry point for Top-Down Adventure game
 * @game    adventure
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
    // Initialize graphics and game state
    sprites_init();
    game_init();
    
    // Enable display features
    SHOW_BKG;
    SHOW_SPRITES;
    DISPLAY_ON;
    
    // Main game loop
    while(1) {
        wait_vbl_done();
        
        // Render first (VRAM safe)
        game_render();
        
        // Then update
        game_handle_input();
        game_update();
    }
}
