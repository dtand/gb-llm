#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>

// Tile indices
#define TILE_EMPTY      0

// Slot symbols (each is 2x2 tiles = 4 tiles)
// Symbol 0: Cherry
#define TILE_CHERRY_TL  1
#define TILE_CHERRY_TR  2
#define TILE_CHERRY_BL  3
#define TILE_CHERRY_BR  4

// Symbol 1: Bell
#define TILE_BELL_TL    5
#define TILE_BELL_TR    6
#define TILE_BELL_BL    7
#define TILE_BELL_BR    8

// Symbol 2: Bar
#define TILE_BAR_TL     9
#define TILE_BAR_TR     10
#define TILE_BAR_BL     11
#define TILE_BAR_BR     12

// Symbol 3: Seven
#define TILE_SEVEN_TL   13
#define TILE_SEVEN_TR   14
#define TILE_SEVEN_BL   15
#define TILE_SEVEN_BR   16

// Symbol 4: Star
#define TILE_STAR_TL    17
#define TILE_STAR_TR    18
#define TILE_STAR_BL    19
#define TILE_STAR_BR    20

// UI elements
#define TILE_BOX_TL     21
#define TILE_BOX_TR     22
#define TILE_BOX_BL     23
#define TILE_BOX_BR     24
#define TILE_BOX_H      25
#define TILE_BOX_V      26
#define TILE_BOX_FILL   27

// Letters
#define TILE_S          28
#define TILE_L          29
#define TILE_O          30
#define TILE_T          31
#define TILE_C          32
#define TILE_I          33
#define TILE_N          34
#define TILE_W          35
#define TILE_P          36
#define TILE_R          37
#define TILE_E          38
#define TILE_A          39
#define TILE_COLON      40
#define TILE_EXCLAIM    41
#define TILE_B          42
#define TILE_D          43

// Numbers
#define TILE_NUM_0      44
#define TILE_NUM_1      45
#define TILE_NUM_2      46
#define TILE_NUM_3      47
#define TILE_NUM_4      48
#define TILE_NUM_5      49
#define TILE_NUM_6      50
#define TILE_NUM_7      51
#define TILE_NUM_8      52
#define TILE_NUM_9      53

// Number of different symbols
#define NUM_SYMBOLS     5

// Symbol payouts (in coins) - also defined in data/symbols.json
#define PAYOUT_CHERRY   5       // @tunable range:1-20 step:1 desc:"Cherry 2-match payout"
#define PAYOUT_BELL     10      // @tunable range:5-30 step:5 desc:"Bell 2-match payout"
#define PAYOUT_BAR      20      // @tunable range:10-50 step:5 desc:"Bar 2-match payout"
#define PAYOUT_SEVEN    50      // @tunable range:20-100 step:10 desc:"Seven 2-match payout"
#define PAYOUT_STAR     100     // @tunable range:50-200 step:25 desc:"Star 2-match payout"

// Initialize tile data
void init_tiles(void);

// Draw a symbol (2x2) at position
void draw_symbol(uint8_t symbol, uint8_t x, uint8_t y);

#endif
