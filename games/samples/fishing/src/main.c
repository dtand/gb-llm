#include <gb/gb.h>
#include "sprites.h"
#include "game.h"

void main(void) {
    // Initialize display
    DISPLAY_OFF;
    
    // Initialize tile data
    init_tiles();
    
    // Initialize game state
    game_init();
    
    // Show background layer
    SHOW_BKG;
    DISPLAY_ON;
    
    // Main game loop
    while (1) {
        // Wait for vblank
        wait_vbl_done();
        
        // Update game logic
        game_update();
    }
}
