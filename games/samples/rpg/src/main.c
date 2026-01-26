/**
 * @file    main.c
 * @brief   Entry point for RPG Battle Demo
 * @game    rpg
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
    // Initialize tile data in VRAM
    sprites_init();
    
    // Initialize game state
    game_init();
    
    // Enable display features
    // Background for battle scene and UI
    // Sprites for hero character
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
