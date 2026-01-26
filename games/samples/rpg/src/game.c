/**
 * @file    game.c
 * @brief   Core game logic for RPG Battle Demo
 * @game    rpg
 * 
 * Demonstrates turn-based combat, menu systems, and stat management.
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
// UI DRAWING FUNCTIONS
// ============================================================

/**
 * @brief   Draw a box with border at given position
 */
static void draw_box(uint8_t x, uint8_t y, uint8_t w, uint8_t h) {
    uint8_t i, j;
    
    // Corners
    set_bkg_tile_xy(x, y, TILE_BORDER_TL);
    set_bkg_tile_xy(x + w - 1, y, TILE_BORDER_TR);
    set_bkg_tile_xy(x, y + h - 1, TILE_BORDER_BL);
    set_bkg_tile_xy(x + w - 1, y + h - 1, TILE_BORDER_BR);
    
    // Top and bottom edges
    for (i = x + 1; i < x + w - 1; i++) {
        set_bkg_tile_xy(i, y, TILE_BORDER_T);
        set_bkg_tile_xy(i, y + h - 1, TILE_BORDER_B);
    }
    
    // Left and right edges
    for (j = y + 1; j < y + h - 1; j++) {
        set_bkg_tile_xy(x, j, TILE_BORDER_L);
        set_bkg_tile_xy(x + w - 1, j, TILE_BORDER_R);
    }
    
    // Fill interior
    for (j = y + 1; j < y + h - 1; j++) {
        for (i = x + 1; i < x + w - 1; i++) {
            set_bkg_tile_xy(i, j, TILE_FILL);
        }
    }
}

/**
 * @brief   Draw a string of text (A-Z only) at position
 */
static void draw_text(uint8_t x, uint8_t y, const char* text) {
    while (*text) {
        char c = *text;
        if (c >= 'A' && c <= 'Z') {
            set_bkg_tile_xy(x, y, TILE_A + (c - 'A'));
        } else if (c >= '0' && c <= '9') {
            set_bkg_tile_xy(x, y, TILE_DIGIT_0 + (c - '0'));
        } else if (c == ':') {
            set_bkg_tile_xy(x, y, TILE_COLON);
        } else if (c == '/') {
            set_bkg_tile_xy(x, y, TILE_SLASH);
        } else if (c == '!') {
            set_bkg_tile_xy(x, y, TILE_EXCLAM);
        } else if (c == ' ') {
            set_bkg_tile_xy(x, y, TILE_FILL);
        }
        x++;
        text++;
    }
}

/**
 * @brief   Draw a number at position (up to 3 digits)
 */
static void draw_number(uint8_t x, uint8_t y, uint8_t num) {
    if (num >= 100) {
        set_bkg_tile_xy(x, y, TILE_DIGIT_0 + (num / 100));
        x++;
        num %= 100;
        set_bkg_tile_xy(x, y, TILE_DIGIT_0 + (num / 10));
        x++;
        set_bkg_tile_xy(x, y, TILE_DIGIT_0 + (num % 10));
    } else if (num >= 10) {
        set_bkg_tile_xy(x, y, TILE_DIGIT_0 + (num / 10));
        x++;
        set_bkg_tile_xy(x, y, TILE_DIGIT_0 + (num % 10));
    } else {
        set_bkg_tile_xy(x, y, TILE_DIGIT_0 + num);
    }
}

/**
 * @brief   Draw HP bar for a combatant
 */
static void draw_hp_bar(uint8_t x, uint8_t y, int8_t hp, int8_t max_hp, uint8_t width) {
    uint8_t i;
    uint8_t filled;
    
    if (hp < 0) hp = 0;
    filled = (uint8_t)(((uint16_t)hp * width) / max_hp);
    
    for (i = 0; i < width; i++) {
        if (i < filled) {
            set_bkg_tile_xy(x + i, y, TILE_HP_FULL);
        } else {
            set_bkg_tile_xy(x + i, y, TILE_HP_EMPTY);
        }
    }
}

/**
 * @brief   Draw MP bar for a combatant
 */
static void draw_mp_bar(uint8_t x, uint8_t y, int8_t mp, int8_t max_mp, uint8_t width) {
    uint8_t i;
    uint8_t filled;
    
    if (mp < 0) mp = 0;
    filled = (uint8_t)(((uint16_t)mp * width) / max_mp);
    
    for (i = 0; i < width; i++) {
        if (i < filled) {
            set_bkg_tile_xy(x + i, y, TILE_MP_FULL);
        } else {
            set_bkg_tile_xy(x + i, y, TILE_MP_EMPTY);
        }
    }
}

/**
 * @brief   Clear the message area (rows 8-9, in open space above stats)
 */
static void clear_message(void) {
    uint8_t i;
    for (i = 0; i < 20; i++) {
        set_bkg_tile_xy(i, 8, TILE_EMPTY);
        set_bkg_tile_xy(i, 9, TILE_EMPTY);
    }
}

// ============================================================
// UI SETUP
// ============================================================

/**
 * @brief   Draw the monster sprite using background tiles
 */
static void draw_monster(void) {
    uint8_t x, y;
    uint8_t tile = TILE_MONSTER_START;
    
    // Draw 4x4 monster at position (centered on right side)
    for (y = 0; y < 4; y++) {
        for (x = 0; x < 4; x++) {
            set_bkg_tile_xy(MONSTER_TILE_X + x, MONSTER_TILE_Y + y, tile);
            tile++;
        }
    }
}

/**
 * @brief   Clear the monster area (when defeated)
 */
static void clear_monster(void) {
    uint8_t x, y;
    
    for (y = 0; y < 4; y++) {
        for (x = 0; x < 4; x++) {
            set_bkg_tile_xy(MONSTER_TILE_X + x, MONSTER_TILE_Y + y, TILE_EMPTY);
        }
    }
}

/**
 * @brief   Set up the battle UI
 */
static void setup_battle_ui(void) {
    uint8_t x, y;
    
    // Clear entire background
    for (y = 0; y < 18; y++) {
        for (x = 0; x < 20; x++) {
            set_bkg_tile_xy(x, y, TILE_EMPTY);
        }
    }
    
    // Draw monster centered (rows 1-4, centered at x=8)
    draw_monster();
    
    // Monster name centered below monster (row 5) - from data table
    const Enemy* enemy_data = &enemies[game.enemy_id];
    draw_text(8, 5, enemy_data->name);
    // Monster HP bar centered (row 6)
    // Bar drawn in render
    
    // Rows 7-10: Open space for messages (drawn dynamically)
    
    // Hero stats box (rows 11-13)
    draw_box(0, 11, 20, 3);
    draw_text(1, 12, "HERO");
    draw_text(6, 12, "HP");
    // HP bar cols 8-13 (6 tiles)
    draw_text(14, 12, "MP");
    // MP bar cols 16-18 (3 tiles)
    
    // Menu box (rows 14-17)
    draw_box(0, 14, 10, 4);
    draw_text(2, 15, "ATTACK");
    draw_text(2, 16, "MAGIC");
    
    // Second column
    draw_box(9, 14, 11, 4);
    draw_text(11, 15, "DEFEND");
    draw_text(11, 16, "FLEE");
}

// ============================================================
// COMBAT LOGIC
// ============================================================

/**
 * @brief   Calculate damage for an attack
 */
static uint8_t calc_damage(uint8_t attack, uint8_t defense, uint8_t defending) {
    int8_t damage;
    uint8_t variance;
    
    // Base damage = attack - defense/2
    damage = attack - (defense / 2);
    
    // If defending, halve damage
    if (defending) {
        damage /= 2;
    }
    
    // Add random variance (-2 to +2)
    variance = rand8() % 5;
    damage = damage - 2 + variance;
    
    // Minimum 1 damage
    if (damage < 1) damage = 1;
    
    return (uint8_t)damage;
}

/**
 * @brief   Execute player attack
 */
static void do_player_attack(void) {
    game.last_damage = calc_damage(game.hero.attack, game.monster.defense, game.monster.defending);
    game.monster.hp -= game.last_damage;
    game.monster.defending = 0;  // Clear defend
    
    clear_message();
    draw_text(4, 8, "ATTACK!");
    draw_number(12, 8, game.last_damage);
    draw_text(15, 8, "DMG");
}

/**
 * @brief   Execute player magic
 */
static void do_player_magic(void) {
    if (game.hero.mp >= MAGIC_COST) {
        game.hero.mp -= MAGIC_COST;
        // Get magic damage from hero data
        const Heroe* hero_data = &heroes[game.hero_id];
        game.last_damage = hero_data->magic_dmg;
        game.monster.hp -= game.last_damage;
        game.monster.defending = 0;
        
        clear_message();
        draw_text(5, 8, "FIRE!");
        draw_number(11, 8, game.last_damage);
        draw_text(14, 8, "DMG");
    } else {
        clear_message();
        draw_text(3, 8, "NOT ENOUGH MP!");
    }
}

/**
 * @brief   Execute player defend
 */
static void do_player_defend(void) {
    game.hero.defending = 1;
    
    clear_message();
    draw_text(5, 8, "DEFENDING!");
}

/**
 * @brief   Attempt to flee
 */
static void do_player_flee(void) {
    uint8_t chance;
    
    game.flee_attempts++;
    chance = 50 + (game.flee_attempts * 15);  // Better odds each try
    
    if ((rand8() % 100) < chance) {
        game.state = STATE_FLEE;
        clear_message();
        draw_text(2, 8, "GOT AWAY SAFELY!");
    } else {
        clear_message();
        draw_text(3, 8, "CANNOT ESCAPE!");
    }
}

/**
 * @brief   Execute enemy turn
 */
static void do_enemy_turn(void) {
    game.last_damage = calc_damage(game.monster.attack, game.hero.defense, game.hero.defending);
    game.hero.hp -= game.last_damage;
    game.hero.defending = 0;  // Clear defend after enemy attacks
    
    clear_message();
    // Show enemy name from data table
    const Enemy* enemy_data = &enemies[game.enemy_id];
    draw_text(3, 8, enemy_data->name);
    draw_number(11, 8, game.last_damage);
    draw_text(14, 8, "DMG");
}

// ============================================================
// INITIALIZATION
// ============================================================

/**
 * @brief   Initialize game state for new battle
 */
void game_init(void) {
    // Select hero and enemy from data tables
    game.hero_id = 0;  // First hero
    game.enemy_id = rand8() % ENEMY_COUNT;  // Random enemy
    
    // Initialize hero from data table
    const Heroe* hero_data = &heroes[game.hero_id];
    game.hero.hp = hero_data->max_hp;
    game.hero.max_hp = hero_data->max_hp;
    game.hero.mp = hero_data->max_mp;
    game.hero.max_mp = hero_data->max_mp;
    game.hero.attack = hero_data->attack;
    game.hero.defense = hero_data->defense;
    game.hero.defending = 0;
    
    // Initialize monster from data table
    const Enemy* enemy_data = &enemies[game.enemy_id];
    game.monster.hp = enemy_data->max_hp;
    game.monster.max_hp = enemy_data->max_hp;
    game.monster.mp = 0;
    game.monster.max_mp = 0;
    game.monster.attack = enemy_data->attack;
    game.monster.defense = enemy_data->defense;
    game.monster.defending = 0;
    
    // Initialize game state
    game.state = STATE_MENU;
    game.menu_cursor = 0;
    game.message_timer = 0;
    game.action_timer = 0;
    game.last_damage = 0;
    game.last_action = 0;
    game.flee_attempts = 0;
    
    // Set up UI
    setup_battle_ui();
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
    
    // Only handle input in menu state
    if (game.state != STATE_MENU) return;
    
    // D-pad navigation
    if ((curr_input & J_UP) && !(prev_input & J_UP)) {
        if (game.menu_cursor == MENU_MAGIC) {
            game.menu_cursor = MENU_ATTACK;
        } else if (game.menu_cursor == MENU_FLEE) {
            game.menu_cursor = MENU_DEFEND;
        }
    }
    if ((curr_input & J_DOWN) && !(prev_input & J_DOWN)) {
        if (game.menu_cursor == MENU_ATTACK) {
            game.menu_cursor = MENU_MAGIC;
        } else if (game.menu_cursor == MENU_DEFEND) {
            game.menu_cursor = MENU_FLEE;
        }
    }
    if ((curr_input & J_LEFT) && !(prev_input & J_LEFT)) {
        if (game.menu_cursor == MENU_DEFEND) {
            game.menu_cursor = MENU_ATTACK;
        } else if (game.menu_cursor == MENU_FLEE) {
            game.menu_cursor = MENU_MAGIC;
        }
    }
    if ((curr_input & J_RIGHT) && !(prev_input & J_RIGHT)) {
        if (game.menu_cursor == MENU_ATTACK) {
            game.menu_cursor = MENU_DEFEND;
        } else if (game.menu_cursor == MENU_MAGIC) {
            game.menu_cursor = MENU_FLEE;
        }
    }
    
    // A button: select action
    if ((curr_input & J_A) && !(prev_input & J_A)) {
        game.state = STATE_PLAYER_TURN;
        game.action_timer = ACTION_DELAY;
        
        switch (game.menu_cursor) {
            case MENU_ATTACK:
                do_player_attack();
                break;
            case MENU_MAGIC:
                do_player_magic();
                break;
            case MENU_DEFEND:
                do_player_defend();
                break;
            case MENU_FLEE:
                do_player_flee();
                break;
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
    // Seed RNG with input timing
    rand_seed ^= curr_input;
    
    switch (game.state) {
        case STATE_MENU:
            // Waiting for input, handled in game_handle_input
            break;
            
        case STATE_PLAYER_TURN:
            // Wait for action animation
            if (game.action_timer > 0) {
                game.action_timer--;
            } else {
                // Check for victory
                if (game.monster.hp <= 0) {
                    game.state = STATE_VICTORY;
                    game.message_timer = MESSAGE_DELAY * 2;
                    clear_monster();
                    clear_message();
                    draw_text(6, 8, "VICTORY!");
                } else if (game.state != STATE_FLEE) {
                    // Enemy turn
                    game.state = STATE_ENEMY_TURN;
                    game.action_timer = ACTION_DELAY;
                    do_enemy_turn();
                }
            }
            break;
            
        case STATE_ENEMY_TURN:
            // Wait for action animation
            if (game.action_timer > 0) {
                game.action_timer--;
            } else {
                // Check for defeat
                if (game.hero.hp <= 0) {
                    game.state = STATE_DEFEAT;
                    game.message_timer = MESSAGE_DELAY * 2;
                    clear_message();
                    draw_text(6, 8, "DEFEAT!");
                } else {
                    // Back to menu
                    game.state = STATE_MENU;
                    clear_message();
                }
            }
            break;
            
        case STATE_VICTORY:
        case STATE_DEFEAT:
        case STATE_FLEE:
            // Wait, then allow restart
            if (game.message_timer > 0) {
                game.message_timer--;
            } else {
                // Show restart prompt
                draw_text(4, 8, "PRESS START");
                
                if ((curr_input & J_START) && !(prev_input & J_START)) {
                    game_init();
                }
            }
            break;
    }
}

// ============================================================
// RENDERING
// ============================================================

/**
 * @brief   Render game state to screen
 */
void game_render(void) {
    // Update hero HP bar (row 12, cols 8-13 = 6 tiles)
    draw_hp_bar(8, 12, game.hero.hp, game.hero.max_hp, 6);
    // Update hero MP bar (row 12, cols 16-18 = 3 tiles)
    draw_mp_bar(16, 12, game.hero.mp, game.hero.max_mp, 3);
    
    // Update monster HP bar centered (row 6, cols 6-13 = 8 tiles)
    draw_hp_bar(6, 6, game.monster.hp, game.monster.max_hp, 8);
    
    // Draw menu cursor
    // Clear all cursor positions first (rows 15-16)
    set_bkg_tile_xy(1, 15, TILE_FILL);
    set_bkg_tile_xy(1, 16, TILE_FILL);
    set_bkg_tile_xy(10, 15, TILE_FILL);
    set_bkg_tile_xy(10, 16, TILE_FILL);
    
    // Draw cursor at current position (only in menu state)
    if (game.state == STATE_MENU) {
        switch (game.menu_cursor) {
            case MENU_ATTACK:
                set_bkg_tile_xy(1, 15, TILE_ARROW);
                break;
            case MENU_MAGIC:
                set_bkg_tile_xy(1, 16, TILE_ARROW);
                break;
            case MENU_DEFEND:
                set_bkg_tile_xy(10, 15, TILE_ARROW);
                break;
            case MENU_FLEE:
                set_bkg_tile_xy(10, 16, TILE_ARROW);
                break;
        }
    }
}
