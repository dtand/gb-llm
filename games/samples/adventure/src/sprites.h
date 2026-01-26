/**
 * @file    sprites.h
 * @brief   Sprite and tile declarations for Top-Down Adventure
 * @game    adventure
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// SPRITE INDICES
// ============================================================

#define SPR_PLAYER          0
#define SPR_NPC             1

// ============================================================
// BACKGROUND TILE INDICES
// ============================================================

#define BG_FLOOR            0
#define BG_WALL             1
#define BG_TREE             2
#define BG_PATH             3
#define BG_DOOR             4
#define BG_DIALOG           5   // Solid dialog background
#define BG_DIALOG_BORDER    6   // Dialog border

// Letter tiles for "HELLO!"
#define BG_H                7
#define BG_E                8
#define BG_L                9
#define BG_O                10
#define BG_EXCLAIM          11

// ============================================================
// FUNCTIONS
// ============================================================

void sprites_init(void);

#endif
