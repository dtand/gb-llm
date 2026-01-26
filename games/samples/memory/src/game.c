/**
 * @file    game.c
 * @brief   Core game logic for Memory Card Game
 * @game    memory
 * 
 * Demonstrates grid-based selection, card flip logic, and match detection.
 */

#include <gb/gb.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"

// ============================================================
// GLOBAL STATE
// ============================================================

GameState game;
static uint8_t prev_input = 0;
static uint8_t curr_input = 0;

// Simple pseudo-random number generator
static uint8_t rand_seed = 42;

/**
 * @brief   Generate pseudo-random number 0-255
 */
static uint8_t rand8(void) {
    rand_seed ^= (rand_seed << 3);
    rand_seed ^= (rand_seed >> 5);
    rand_seed ^= (rand_seed << 4);
    return rand_seed;
}

// ============================================================
// CARD DRAWING FUNCTIONS
// ============================================================

/**
 * @brief   Get screen X position for card at grid position
 */
static uint8_t card_screen_x(uint8_t grid_x) {
    return GRID_START_X + (grid_x * CARD_SPACING_X);
}

/**
 * @brief   Get screen Y position for card at grid position
 */
static uint8_t card_screen_y(uint8_t grid_y) {
    return GRID_START_Y + (grid_y * CARD_SPACING_Y);
}

/**
 * @brief   Draw a single card at its grid position
 */
static void draw_card(uint8_t index) {
    uint8_t grid_x = index % GRID_COLS;
    uint8_t grid_y = index / GRID_COLS;
    uint8_t screen_x = card_screen_x(grid_x);
    uint8_t screen_y = card_screen_y(grid_y);
    uint8_t tile;
    
    Card* card = &game.cards[index];
    
    // Determine which tile to show
    if (card->state == CARD_MATCHED) {
        tile = TILE_CARD_MATCHED;
    } else if (card->state == CARD_FACE_UP) {
        // Show the symbol (TILE_CARD_STAR + symbol index)
        tile = TILE_CARD_STAR + card->symbol;
    } else {
        // Face down
        tile = TILE_CARD_BACK;
    }
    
    // Draw card as single tile (simplified)
    set_bkg_tile_xy(screen_x, screen_y, tile);
}

/**
 * @brief   Draw all cards
 */
static void draw_all_cards(void) {
    uint8_t i;
    for (i = 0; i < TOTAL_CARDS; i++) {
        draw_card(i);
    }
}

/**
 * @brief   Draw the cursor around the selected card
 */
static void draw_cursor(void) {
    uint8_t screen_x = card_screen_x(game.cursor_x);
    uint8_t screen_y = card_screen_y(game.cursor_y);
    
    // Draw cursor corners around the card
    set_bkg_tile_xy(screen_x - 1, screen_y - 1, TILE_CURSOR_TL);
    set_bkg_tile_xy(screen_x + 1, screen_y - 1, TILE_CURSOR_TR);
    set_bkg_tile_xy(screen_x - 1, screen_y + 1, TILE_CURSOR_BL);
    set_bkg_tile_xy(screen_x + 1, screen_y + 1, TILE_CURSOR_BR);
}

/**
 * @brief   Clear cursor from old position
 */
static void clear_cursor(void) {
    uint8_t screen_x = card_screen_x(game.cursor_x);
    uint8_t screen_y = card_screen_y(game.cursor_y);
    
    set_bkg_tile_xy(screen_x - 1, screen_y - 1, TILE_EMPTY);
    set_bkg_tile_xy(screen_x + 1, screen_y - 1, TILE_EMPTY);
    set_bkg_tile_xy(screen_x - 1, screen_y + 1, TILE_EMPTY);
    set_bkg_tile_xy(screen_x + 1, screen_y + 1, TILE_EMPTY);
}

// ============================================================
// UI DRAWING
// ============================================================

/**
 * @brief   Draw the moves counter
 */
static void draw_moves(void) {
    // "MOVES:" at row 0
    set_bkg_tile_xy(0, 0, TILE_M);
    set_bkg_tile_xy(1, 0, TILE_O);
    set_bkg_tile_xy(2, 0, TILE_V);
    set_bkg_tile_xy(3, 0, TILE_E);
    set_bkg_tile_xy(4, 0, TILE_S);
    set_bkg_tile_xy(5, 0, TILE_COLON);
    
    // Draw move count (2 digits)
    set_bkg_tile_xy(6, 0, TILE_DIGIT_0 + (game.moves / 10));
    set_bkg_tile_xy(7, 0, TILE_DIGIT_0 + (game.moves % 10));
}

/**
 * @brief   Draw pairs matched counter
 */
static void draw_pairs(void) {
    // "PAIRS:" at row 0, right side
    set_bkg_tile_xy(12, 0, TILE_P);
    set_bkg_tile_xy(13, 0, TILE_A);
    set_bkg_tile_xy(14, 0, TILE_I);
    set_bkg_tile_xy(15, 0, TILE_R);
    set_bkg_tile_xy(16, 0, TILE_S);
    set_bkg_tile_xy(17, 0, TILE_COLON);
    
    // Draw pairs count
    set_bkg_tile_xy(18, 0, TILE_DIGIT_0 + game.pairs_matched);
}

/**
 * @brief   Draw victory message
 */
static void draw_victory(void) {
    // "WIN!" centered
    set_bkg_tile_xy(8, 1, TILE_W);
    set_bkg_tile_xy(9, 1, TILE_I);
    set_bkg_tile_xy(10, 1, TILE_N);
}

/**
 * @brief   Clear victory message area
 */
static void clear_victory(void) {
    set_bkg_tile_xy(8, 1, TILE_EMPTY);
    set_bkg_tile_xy(9, 1, TILE_EMPTY);
    set_bkg_tile_xy(10, 1, TILE_EMPTY);
}

// ============================================================
// CARD SHUFFLING
// ============================================================

/**
 * @brief   Shuffle the cards using Fisher-Yates
 */
static void shuffle_cards(void) {
    uint8_t i, j, temp_symbol, temp_state;
    
    // First, set up pairs: 2 of each symbol
    for (i = 0; i < TOTAL_CARDS; i++) {
        game.cards[i].symbol = i / 2;  // 0,0,1,1,2,2,...,7,7
        game.cards[i].state = CARD_FACE_DOWN;
    }
    
    // Fisher-Yates shuffle
    for (i = TOTAL_CARDS - 1; i > 0; i--) {
        j = rand8() % (i + 1);
        
        // Swap cards[i] and cards[j]
        temp_symbol = game.cards[i].symbol;
        temp_state = game.cards[i].state;
        
        game.cards[i].symbol = game.cards[j].symbol;
        game.cards[i].state = game.cards[j].state;
        
        game.cards[j].symbol = temp_symbol;
        game.cards[j].state = temp_state;
    }
}

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state for new game
 */
void game_init(void) {
    uint8_t x, y;
    
    // Clear screen
    for (y = 0; y < 18; y++) {
        for (x = 0; x < 20; x++) {
            set_bkg_tile_xy(x, y, TILE_EMPTY);
        }
    }
    
    // Initialize game state
    game.cursor_x = 0;
    game.cursor_y = 0;
    game.first_card = 0;
    game.second_card = 0;
    game.state = STATE_SELECTING_FIRST;
    game.show_timer = 0;
    game.pairs_matched = 0;
    game.moves = 0;
    
    // Shuffle and set up cards
    shuffle_cards();
    
    // Draw initial UI
    draw_moves();
    draw_pairs();
    draw_all_cards();
    draw_cursor();
}

// ============================================================
// INPUT HANDLING
// ============================================================

/**
 * @brief   Handle player input
 */
void game_handle_input(void) {
    uint8_t card_index;
    Card* card;
    
    prev_input = curr_input;
    curr_input = joypad();
    
    // Seed RNG with input timing
    rand_seed ^= curr_input;
    
    // Handle victory state - press START to restart
    if (game.state == STATE_VICTORY) {
        if ((curr_input & J_START) && !(prev_input & J_START)) {
            game_init();
        }
        return;
    }
    
    // Don't allow input while showing cards
    if (game.state == STATE_SHOWING_CARDS) {
        return;
    }
    
    // D-pad movement
    if ((curr_input & J_UP) && !(prev_input & J_UP)) {
        if (game.cursor_y > 0) {
            clear_cursor();
            game.cursor_y--;
            draw_cursor();
        }
    }
    if ((curr_input & J_DOWN) && !(prev_input & J_DOWN)) {
        if (game.cursor_y < GRID_ROWS - 1) {
            clear_cursor();
            game.cursor_y++;
            draw_cursor();
        }
    }
    if ((curr_input & J_LEFT) && !(prev_input & J_LEFT)) {
        if (game.cursor_x > 0) {
            clear_cursor();
            game.cursor_x--;
            draw_cursor();
        }
    }
    if ((curr_input & J_RIGHT) && !(prev_input & J_RIGHT)) {
        if (game.cursor_x < GRID_COLS - 1) {
            clear_cursor();
            game.cursor_x++;
            draw_cursor();
        }
    }
    
    // A button - select card
    if ((curr_input & J_A) && !(prev_input & J_A)) {
        card_index = game.cursor_y * GRID_COLS + game.cursor_x;
        card = &game.cards[card_index];
        
        // Can't select already matched or face-up cards
        if (card->state != CARD_FACE_DOWN) {
            return;
        }
        
        // Flip the card face up
        card->state = CARD_FACE_UP;
        draw_card(card_index);
        
        if (game.state == STATE_SELECTING_FIRST) {
            // First card selected
            game.first_card = card_index;
            game.state = STATE_SELECTING_SECOND;
        } else if (game.state == STATE_SELECTING_SECOND) {
            // Second card selected
            game.second_card = card_index;
            game.moves++;
            draw_moves();
            
            // Start showing timer
            game.state = STATE_SHOWING_CARDS;
            game.show_timer = SHOW_DELAY;
        }
    }
}

// ============================================================
// UPDATE LOGIC
// ============================================================

/**
 * @brief   Update game logic
 */
void game_update(void) {
    Card* first;
    Card* second;
    
    if (game.state == STATE_SHOWING_CARDS) {
        if (game.show_timer > 0) {
            game.show_timer--;
        } else {
            // Timer expired - check for match
            first = &game.cards[game.first_card];
            second = &game.cards[game.second_card];
            
            if (first->symbol == second->symbol) {
                // Match! Mark both as matched
                first->state = CARD_MATCHED;
                second->state = CARD_MATCHED;
                game.pairs_matched++;
                draw_pairs();
                
                // Check for victory
                if (game.pairs_matched == NUM_PAIRS) {
                    game.state = STATE_VICTORY;
                    draw_victory();
                    return;
                }
            } else {
                // No match - flip both back
                first->state = CARD_FACE_DOWN;
                second->state = CARD_FACE_DOWN;
            }
            
            // Redraw the cards
            draw_card(game.first_card);
            draw_card(game.second_card);
            
            // Back to selecting first card
            game.state = STATE_SELECTING_FIRST;
        }
    }
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Render game state to screen
 */
void game_render(void) {
    // Most rendering is done immediately when state changes
    // This function can be used for animations if needed
}
