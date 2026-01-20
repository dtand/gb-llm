#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"

void main(void) {
    // Initialize graphics and game state
    init_sprites();
    init_game();
    
    // Enable display features
    SHOW_BKG;
    SHOW_SPRITES;
    DISPLAY_ON;
    
    // Main game loop
    while(1) {
        // Wait for vertical blank (sync to ~60fps)
        wait_vbl_done();
        
        // Process input and update game
        handle_input();
        update_game();
        render_game();
    }
}
