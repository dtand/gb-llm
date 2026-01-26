/**
 * @file    main.c
 * @brief   Entry point for Space Shooter game
 * @game    shooter
 * 
 * Initializes the game and runs the main loop.
 * All game logic is delegated to game.c
 */

#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"

/**
 * @brief   Main entry point
 * 
 * Initializes graphics and game state, then runs the
 * main game loop at ~60fps using vsync.
 */
void main(void) {
    // Initialize graphics and game state
    sprites_init();
    game_init();
    
    // Enable display features
    // Window layer for HUD, background for starfield, sprites for gameplay
    SHOW_WIN;
    SHOW_BKG;
    SHOW_SPRITES;
    DISPLAY_ON;
    
    // Main game loop
    while(1) {
        // Wait for vertical blank (sync to ~60fps)
        wait_vbl_done();
        
        // Process input and update game
        game_handle_input();
        game_update();
        game_render();
    }
}
