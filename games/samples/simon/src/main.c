// Simon - Main Entry Point
// Pattern memory game with sound

#include <gb/gb.h>
#include "sprites.h"
#include "game.h"

void main(void) {
    // Disable interrupts during setup
    disable_interrupts();
    
    // Initialize graphics and sound
    sprites_init();
    
    // Initialize game state
    game_init();
    
    // Enable interrupts
    enable_interrupts();
    
    // Main game loop
    while (1) {
        // Wait for vblank
        wait_vbl_done();
        
        // Handle input
        game_handle_input();
        
        // Update game logic
        game_update();
        
        // Draw
        game_draw();
    }
}
