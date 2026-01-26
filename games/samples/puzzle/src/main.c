/**
 * @file    main.c
 * @brief   Entry point for Falling Block Puzzle game
 * @game    puzzle
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
    
    // Enable display features (background only, no sprites)
    SHOW_BKG;
    DISPLAY_ON;
    
    // Main game loop
    while(1) {
        // Wait for vertical blank (sync to ~60fps)
        wait_vbl_done();
        
        // Render FIRST while still in VBlank - VRAM writes are only safe during VBlank
        game_render();
        
        // Then process input and update game state (no VRAM access)
        game_handle_input();
        game_update();
    }
}
