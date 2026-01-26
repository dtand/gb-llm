/**
 * @file    game.h
 * @brief   Game state and constants for RPG Battle Demo
 * @game    rpg
 */

#ifndef GAME_H
#define GAME_H

#include <stdint.h>
#include "../build/data.h"

// ============================================================
// GAME CONSTANTS
// ============================================================

// Battle states
#define STATE_MENU          0   // Player selecting action
#define STATE_PLAYER_TURN   1   // Player action executing
#define STATE_ENEMY_TURN    2   // Enemy action executing
#define STATE_MESSAGE       3   // Displaying message
#define STATE_VICTORY       4   // Player won
#define STATE_DEFEAT        5   // Player lost
#define STATE_FLEE          6   // Player fled

// Menu options
#define MENU_ATTACK     0
#define MENU_MAGIC      1
#define MENU_DEFEND     2
#define MENU_FLEE       3
#define MENU_COUNT      4

// Combat constants (not in data tables)
#define MAGIC_COST      5   // @tunable range:1-20 step:1 desc:"MP cost for magic attack"

// Timing
#define MESSAGE_DELAY   60  // @tunable range:30-120 step:10 desc:"Frames to show message"
#define ACTION_DELAY    30  // @tunable range:15-60 step:5 desc:"Frames for action animation"

// ============================================================
// DATA STRUCTURES
// ============================================================

/**
 * @brief   Combatant stats (hero or monster)
 */
typedef struct {
    int8_t hp;          // Current HP (signed for damage calc)
    int8_t max_hp;      // Maximum HP
    int8_t mp;          // Current MP
    int8_t max_mp;      // Maximum MP
    uint8_t attack;     // Attack power
    uint8_t defense;    // Defense value
    uint8_t defending;  // Is defending this turn?
} Combatant;

/**
 * @brief   Complete game state
 */
typedef struct {
    Combatant hero;
    Combatant monster;
    
    uint8_t state;          // Current battle state
    uint8_t menu_cursor;    // Selected menu option (0-3)
    uint8_t message_timer;  // Countdown for message display
    uint8_t action_timer;   // Countdown for action animation
    
    uint8_t last_damage;    // Damage dealt in last action
    uint8_t last_action;    // What action was taken
    
    uint8_t flee_attempts;  // Number of flee attempts
    
    uint8_t hero_id;        // Index into heroes[] data table
    uint8_t enemy_id;       // Index into enemies[] data table
} GameState;

// ============================================================
// GLOBAL STATE
// ============================================================

extern GameState game;

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

/**
 * @brief   Initialize game state for new battle
 */
void game_init(void);

/**
 * @brief   Handle player input
 */
void game_handle_input(void);

/**
 * @brief   Update game logic
 */
void game_update(void);

/**
 * @brief   Render game state to screen
 */
void game_render(void);

#endif /* GAME_H */
