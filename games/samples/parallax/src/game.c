/**
 * @file    game.c
 * @brief   Core game logic for Parallax Scroller
 * @game    parallax
 * 
 * Demonstrates parallax scrolling using LYC interrupts to change
 * the scroll register at different scanlines.
 */

#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"

// ============================================================
// GLOBAL STATE
// ============================================================

GameState game;
uint8_t prev_input = 0;
uint8_t curr_input = 0;

// Layer scroll values (volatile - accessed by interrupt)
volatile uint8_t layer_scroll_mountain = 0;
volatile uint8_t layer_scroll_hills = 0;
volatile uint8_t layer_scroll_ground = 0;

// Current layer being processed by interrupt
static volatile uint8_t current_layer = 0;

// ============================================================
// LCD INTERRUPT
// ============================================================

/**
 * @brief   LCD STAT interrupt handler
 * 
 * Called at specific scanlines (set by LYC_REG) to change
 * the scroll register for parallax effect.
 */
void lcd_isr(void) {
    switch (current_layer) {
        case 0:
            // At mountain start - set mountain scroll
            SCX_REG = layer_scroll_mountain;
            LYC_REG = HILLS_START;
            current_layer = 1;
            break;
            
        case 1:
            // At hills start - set hills scroll
            SCX_REG = layer_scroll_hills;
            LYC_REG = GROUND_START;
            current_layer = 2;
            break;
            
        case 2:
            // At ground start - set ground scroll
            SCX_REG = layer_scroll_ground;
            LYC_REG = MOUNTAIN_START;
            current_layer = 0;
            break;
    }
}

// ============================================================
// BACKGROUND SETUP
// ============================================================

/**
 * @brief   Draw the layered background
 */
static void setup_background(void) {
    uint8_t x, y;
    
    // Sky region (rows 0-3, tiles)
    for (y = 0; y < 4; y++) {
        for (x = 0; x < 32; x++) {
            set_bkg_tile_xy(x, y, TILE_SKY);
        }
    }
    
    // Mountain region (rows 4-7)
    // Draw mountain silhouette
    for (x = 0; x < 32; x++) {
        // Create varied mountain heights
        uint8_t height = ((x * 3) % 4);  // 0-3 tiles of mountain
        
        for (y = 4; y < 8; y++) {
            if (y >= (7 - height)) {
                set_bkg_tile_xy(x, y, TILE_MOUNTAIN);
            } else {
                set_bkg_tile_xy(x, y, TILE_SKY);
            }
        }
    }
    
    // Hills region (rows 8-11)
    for (x = 0; x < 32; x++) {
        uint8_t height = ((x * 5 + 2) % 3);  // 0-2 tiles of hills
        
        for (y = 8; y < 12; y++) {
            if (y >= (11 - height)) {
                set_bkg_tile_xy(x, y, TILE_HILLS);
            } else {
                set_bkg_tile_xy(x, y, TILE_SKY);
            }
        }
    }
    
    // Ground region (rows 12-17) with visible markers
    for (y = 12; y < 18; y++) {
        for (x = 0; x < 32; x++) {
            if (y == 12) {
                // Grass top with trees every 5 tiles
                if ((x % 5) == 0) {
                    set_bkg_tile_xy(x, y, TILE_TREE);
                } else {
                    set_bkg_tile_xy(x, y, TILE_GRASS);
                }
            } else if (y == 13) {
                // Row with rocks every 7 tiles, offset
                if (((x + 3) % 7) == 0) {
                    set_bkg_tile_xy(x, y, TILE_ROCK);
                } else {
                    set_bkg_tile_xy(x, y, TILE_GROUND);
                }
            } else {
                // Dirt below with occasional rocks
                if ((x % 11) == (y % 11)) {
                    set_bkg_tile_xy(x, y, TILE_ROCK);
                } else {
                    set_bkg_tile_xy(x, y, TILE_GROUND);
                }
            }
        }
    }
}

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state
 */
void game_init(void) {
    game.scroll_x = 0;
    game.scroll_sky = 0;
    game.scroll_mountain = 0;
    game.scroll_hills = 0;
    game.scroll_ground = 0;
    game.moving = 0;
    game.direction = 0;
    game.fast_mode = 0;
    
    // Set up the background tiles
    setup_background();
    
    // Initialize layer scroll values
    layer_scroll_mountain = 0;
    layer_scroll_hills = 0;
    layer_scroll_ground = 0;
    current_layer = 0;
    
    // Set up LCD interrupt for parallax
    // LYC triggers interrupt when LY == LYC
    STAT_REG |= 0x40;       // Enable LYC=LY interrupt
    LYC_REG = MOUNTAIN_START;  // First interrupt at mountain layer
    
    // Register LCD interrupt handler
    add_LCD(lcd_isr);
    
    // Enable LCD and VBlank interrupts
    set_interrupts(VBL_IFLAG | LCD_IFLAG);
    enable_interrupts();
    
    // Initial scroll position (sky doesn't scroll)
    SCX_REG = 0;
}

// ============================================================
// INPUT HANDLING
// ============================================================

/**
 * @brief   Handle player input
 */
void game_handle_input(void) {
    prev_input = curr_input;
    curr_input = joypad();
    
    // Default: auto-scroll right slowly
    game.direction = 1;
    game.fast_mode = 0;
    
    // D-pad controls scroll direction
    if (curr_input & J_LEFT) {
        game.direction = -1;
        game.fast_mode = 1;  // Manual control = faster
    }
    if (curr_input & J_RIGHT) {
        game.direction = 1;
        game.fast_mode = 1;  // Manual control = faster
    }
    
    // A button = stop scrolling
    if (curr_input & J_A) {
        game.direction = 0;
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Update game state
 */
void game_update(void) {
    int16_t speed;
    
    // Calculate scroll speed
    speed = 1;  // Base auto-scroll speed
    if (game.fast_mode) {
        speed = 3;  // Faster when pressing d-pad
    }
    
    // Apply direction (0 = stopped)
    if (game.direction != 0) {
        game.scroll_x += speed * game.direction;
    }
    
    // Calculate layer scroll positions with parallax ratios
    // Ground = full speed (scroll_x)
    // Hills = 1/2 speed
    // Mountains = 1/4 speed
    // Sky = static (0)
    
    game.scroll_ground = (uint8_t)(game.scroll_x & 0xFF);
    game.scroll_hills = (uint8_t)((game.scroll_x >> 1) & 0xFF);
    game.scroll_mountain = (uint8_t)((game.scroll_x >> 2) & 0xFF);
    game.scroll_sky = 0;
    
    // Update volatile copies for interrupt handler
    layer_scroll_mountain = game.scroll_mountain;
    layer_scroll_hills = game.scroll_hills;
    layer_scroll_ground = game.scroll_ground;
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Render game (set sky scroll during VBlank)
 */
void game_render(void) {
    // Set sky scroll (top of frame, before first LYC interrupt)
    SCX_REG = game.scroll_sky;
    
    // Reset interrupt state for new frame
    LYC_REG = MOUNTAIN_START;
    current_layer = 0;
}
