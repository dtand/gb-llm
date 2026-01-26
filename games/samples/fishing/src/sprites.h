#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>

// Background tiles
#define TILE_EMPTY      0
#define TILE_WATER1     1   // Water animation frame 1
#define TILE_WATER2     2   // Water animation frame 2
#define TILE_DOCK       3   // Dock/pier
#define TILE_GRASS      4   // Shore grass

// Bobber tiles (2x2)
#define TILE_BOBBER_TL  5
#define TILE_BOBBER_TR  6
#define TILE_BOBBER_BL  7
#define TILE_BOBBER_BR  8

// Fish tiles (2x2)
#define TILE_FISH_TL    9
#define TILE_FISH_TR    10
#define TILE_FISH_BL    11
#define TILE_FISH_BR    12

// Exclamation mark (bite indicator)
#define TILE_EXCLAIM_T  13
#define TILE_EXCLAIM_B  14

// Rod/line
#define TILE_ROD        15
#define TILE_LINE       16

// Fisherman (2x3 tiles)
#define TILE_MAN_TL     50  // Head left
#define TILE_MAN_TR     51  // Head right  
#define TILE_MAN_ML     52  // Body left
#define TILE_MAN_MR     53  // Body right (arm with rod)
#define TILE_MAN_BL     54  // Legs left
#define TILE_MAN_BR     55  // Legs right

// Letters
#define TILE_F          17
#define TILE_I          18
#define TILE_S          19
#define TILE_H          20
#define TILE_N          21
#define TILE_G          22
#define TILE_C          23
#define TILE_A          24
#define TILE_T          25
#define TILE_W          26
#define TILE_P          27
#define TILE_R          28
#define TILE_E          29
#define TILE_O          30
#define TILE_L          31
#define TILE_D          32
#define TILE_B          33
#define TILE_COLON      34
#define TILE_EXCLAIM    35
#define TILE_M          36

// Numbers
#define TILE_NUM_0      40
#define TILE_NUM_1      41
#define TILE_NUM_2      42
#define TILE_NUM_3      43
#define TILE_NUM_4      44
#define TILE_NUM_5      45
#define TILE_NUM_6      46
#define TILE_NUM_7      47
#define TILE_NUM_8      48
#define TILE_NUM_9      49

// Timing constants
#define BITE_WINDOW     30      // @tunable range:15-60 step:5 desc:"Frames to react when fish bites"
#define MIN_WAIT        60      // @tunable range:30-120 step:15 desc:"Minimum wait before bite"
#define MAX_WAIT        240     // @tunable range:120-480 step:30 desc:"Maximum wait before bite"

// Initialize tile data
void init_tiles(void);

#endif
