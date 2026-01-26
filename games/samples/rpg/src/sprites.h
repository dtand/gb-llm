/**
 * @file    sprites.h
 * @brief   Tile definitions for RPG Battle Demo
 * @game    rpg
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <stdint.h>

// ============================================================
// BACKGROUND TILE INDICES
// ============================================================

#define TILE_EMPTY      0
#define TILE_BORDER_TL  1   // Top-left corner
#define TILE_BORDER_T   2   // Top edge
#define TILE_BORDER_TR  3   // Top-right corner
#define TILE_BORDER_L   4   // Left edge
#define TILE_BORDER_R   5   // Right edge
#define TILE_BORDER_BL  6   // Bottom-left corner
#define TILE_BORDER_B   7   // Bottom edge
#define TILE_BORDER_BR  8   // Bottom-right corner
#define TILE_FILL       9   // Box fill

// Digits 0-9
#define TILE_DIGIT_0    10
#define TILE_DIGIT_1    11
#define TILE_DIGIT_2    12
#define TILE_DIGIT_3    13
#define TILE_DIGIT_4    14
#define TILE_DIGIT_5    15
#define TILE_DIGIT_6    16
#define TILE_DIGIT_7    17
#define TILE_DIGIT_8    18
#define TILE_DIGIT_9    19

// Letters for menu
#define TILE_A          20
#define TILE_B          21
#define TILE_C          22
#define TILE_D          23
#define TILE_E          24
#define TILE_F          25
#define TILE_G          26
#define TILE_H          27
#define TILE_I          28
#define TILE_J          29
#define TILE_K          30
#define TILE_L          31
#define TILE_M          32
#define TILE_N          33
#define TILE_O          34
#define TILE_P          35
#define TILE_Q          36
#define TILE_R          37
#define TILE_S          38
#define TILE_T          39
#define TILE_U          40
#define TILE_V          41
#define TILE_W          42
#define TILE_X          43
#define TILE_Y          44
#define TILE_Z          45

// Special characters
#define TILE_COLON      46
#define TILE_SLASH      47
#define TILE_ARROW      48  // Menu cursor
#define TILE_HP_FULL    49  // HP bar full segment
#define TILE_HP_EMPTY   50  // HP bar empty segment
#define TILE_MP_FULL    51  // MP bar full segment  
#define TILE_MP_EMPTY   52  // MP bar empty segment
#define TILE_EXCLAM     53  // Exclamation mark

// Monster sprite tiles (4x4 = 16 tiles for 32x32 monster)
#define TILE_MONSTER_START  54

// Hero sprite tiles (2x2 = 4 tiles for 16x16 hero)
#define TILE_HERO_START     70

// ============================================================
// SPRITE INDICES (OAM) - Not used in this demo
// ============================================================

// ============================================================
// POSITIONS
// ============================================================

#define MONSTER_TILE_X  8       // Monster centered (20-4)/2 = 8
#define MONSTER_TILE_Y  1       // Top area

// ============================================================
// FUNCTION DECLARATIONS
// ============================================================

/**
 * @brief   Initialize all tile data in VRAM
 */
void sprites_init(void);

#endif /* SPRITES_H */
