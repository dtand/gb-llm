/**
 * @file    game.c
 * @brief   Core game logic for Timer Challenge
 * @game    timer
 * 
 * Demonstrates timer interrupts for precise millisecond timing.
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

// Interrupt tick counter (increments faster than 1ms)
static volatile uint16_t timer_ticks = 0;

// Simple pseudo-random number generator
static uint16_t rand_seed = 12345;

/**
 * @brief   Generate pseudo-random number 0-65535
 */
static uint16_t rand16(void) {
    rand_seed ^= (rand_seed << 7);
    rand_seed ^= (rand_seed >> 9);
    rand_seed ^= (rand_seed << 8);
    return rand_seed;
}

// ============================================================
// TIMER INTERRUPT
// ============================================================

/**
 * @brief   Timer interrupt service routine
 * 
 * Called approximately 1024 times per second with TAC clock 01.
 * Each tick is ~1ms (close enough for reaction timing).
 */
void timer_isr(void) {
    timer_ticks++;
}

/**
 * @brief   Get elapsed milliseconds from tick counter
 */
static uint16_t get_elapsed_ms(void) {
    uint16_t ticks;
    
    // Disable interrupts briefly to read volatile safely
    disable_interrupts();
    ticks = timer_ticks;
    enable_interrupts();
    
    // At 1024 Hz, ticks ~= milliseconds (close enough)
    return ticks;
}

/**
 * @brief   Reset the timer counter
 */
static void reset_timer(void) {
    disable_interrupts();
    timer_ticks = 0;
    enable_interrupts();
}

// ============================================================
// DISPLAY FUNCTIONS
// ============================================================

/**
 * @brief   Clear the screen
 */
static void clear_screen(void) {
    uint8_t x, y;
    
    for (y = 0; y < SCREEN_TILES_Y; y++) {
        for (x = 0; x < SCREEN_TILES_X; x++) {
            set_bkg_tile_xy(x, y, TILE_EMPTY);
        }
    }
}

/**
 * @brief   Display a string at tile position
 */
static void draw_text(uint8_t x, uint8_t y, const char* str) {
    while (*str) {
        char c = *str++;
        uint8_t tile;
        
        if (c >= '0' && c <= '9') {
            tile = TILE_DIGIT_0 + (c - '0');
        } else if (c >= 'A' && c <= 'Z') {
            tile = TILE_LETTER_A + (c - 'A');
        } else if (c == ':') {
            tile = TILE_COLON;
        } else if (c == '!') {
            tile = TILE_EXCLAIM;
        } else if (c == ' ') {
            tile = TILE_EMPTY;
        } else {
            tile = TILE_EMPTY;
        }
        
        set_bkg_tile_xy(x++, y, tile);
    }
}

/**
 * @brief   Display a number at tile position (right-aligned, 4 digits)
 */
static void draw_number(uint8_t x, uint8_t y, uint16_t num) {
    uint8_t digits[4];
    uint8_t i;
    
    // Extract digits
    for (i = 0; i < 4; i++) {
        digits[3 - i] = num % 10;
        num /= 10;
    }
    
    // Display digits
    for (i = 0; i < 4; i++) {
        set_bkg_tile_xy(x + i, y, TILE_DIGIT_0 + digits[i]);
    }
}

// ============================================================
// SCREEN STATES
// ============================================================

/**
 * @brief   Draw title screen
 */
static void draw_title_screen(void) {
    clear_screen();
    draw_text(4, 4, "REACTION TIME");
    draw_text(6, 6, "TEST");
    draw_text(3, 10, "PRESS START");
    
    if (game.best_time < 9999) {
        draw_text(5, 14, "BEST:");
        draw_number(10, 14, game.best_time);
        draw_text(14, 14, "MS");
    }
}

/**
 * @brief   Draw waiting screen
 */
static void draw_waiting_screen(void) {
    clear_screen();
    draw_text(6, 8, "WAIT FOR");
    draw_text(8, 10, "IT");
}

/**
 * @brief   Draw GO screen
 */
static void draw_go_screen(void) {
    clear_screen();
    draw_text(8, 8, "GO!");
}

/**
 * @brief   Draw result screen
 */
static void draw_result_screen(void) {
    clear_screen();
    draw_text(4, 6, "YOUR TIME:");
    draw_number(7, 8, game.reaction_time);
    draw_text(11, 8, "MS");
    
    if (game.reaction_time <= game.best_time) {
        draw_text(5, 11, "NEW BEST!");
    }
    
    draw_text(3, 15, "PRESS A TO");
    draw_text(4, 16, "TRY AGAIN");
}

/**
 * @brief   Draw false start screen
 */
static void draw_false_start_screen(void) {
    clear_screen();
    draw_text(3, 8, "TOO EARLY!");
    draw_text(3, 12, "PRESS A TO");
    draw_text(4, 13, "TRY AGAIN");
}

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state
 */
void game_init(void) {
    game.state = STATE_TITLE;
    game.timer_ms = 0;
    game.delay_target = 0;
    game.reaction_time = 0;
    game.best_time = 9999;  // No best time yet
    
    // Set up timer interrupt
    // TMA = Timer Modulo (value TIMA resets to after overflow)
    // TAC = Timer Control: bit 2 = enable, bits 1-0 = clock select
    // Clock 01 = 262144 Hz, overflows every 256 ticks = 1024 Hz (~1ms)
    TMA_REG = 0x00;         // Reset to 0 on overflow
    TAC_REG = 0x05;         // Enable timer, 262144 Hz clock (1024 interrupts/sec)
    
    // Register interrupt handler
    add_TIM(timer_isr);
    
    // Enable timer and vblank interrupts
    set_interrupts(VBL_IFLAG | TIM_IFLAG);
    enable_interrupts();
    
    draw_title_screen();
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
    
    // Edge detection for button press
    uint8_t pressed = curr_input & ~prev_input;
    
    switch (game.state) {
        case STATE_TITLE:
            if (pressed & J_START) {
                // Generate random delay (1000-3000ms)
                game.delay_target = MIN_DELAY_MS + (rand16() % (MAX_DELAY_MS - MIN_DELAY_MS));
                reset_timer();
                game.state = STATE_WAITING;
                draw_waiting_screen();
            }
            break;
            
        case STATE_WAITING:
            if (pressed & J_A) {
                // False start!
                game.state = STATE_FALSE_START;
                draw_false_start_screen();
            }
            break;
            
        case STATE_READY:
            if (pressed & J_A) {
                // Got it! Record reaction time
                game.reaction_time = get_elapsed_ms();
                
                // Update best time
                if (game.reaction_time < game.best_time) {
                    game.best_time = game.reaction_time;
                }
                
                game.state = STATE_RESULT;
                draw_result_screen();
            }
            break;
            
        case STATE_RESULT:
        case STATE_FALSE_START:
            if (pressed & J_A) {
                // Try again
                game.delay_target = MIN_DELAY_MS + (rand16() % (MAX_DELAY_MS - MIN_DELAY_MS));
                reset_timer();
                game.state = STATE_WAITING;
                draw_waiting_screen();
            }
            break;
    }
    
    // Seed RNG with input timing for more randomness
    if (curr_input) {
        rand_seed ^= timer_ticks;
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Update game state
 */
void game_update(void) {
    if (game.state == STATE_WAITING) {
        // Check if delay has elapsed
        if (get_elapsed_ms() >= game.delay_target) {
            // Time to show GO!
            reset_timer();
            game.state = STATE_READY;
            draw_go_screen();
        }
    }
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Render game (most rendering is event-driven)
 */
void game_render(void) {
    // Most rendering is done on state change
    // This could be used for animations if needed
}
