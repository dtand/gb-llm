#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>

// Tile indices
#define TILE_EMPTY      0
#define TILE_WALL       1
#define TILE_FLOOR      2
#define TILE_PLAYER     3
#define TILE_EXIT       4
#define TILE_VISITED    5   // Breadcrumb trail

// Letters for text
#define TILE_M          6
#define TILE_A          7
#define TILE_Z          8
#define TILE_E          9
#define TILE_W          10
#define TILE_I          11
#define TILE_N          12
#define TILE_S          13
#define TILE_T          14
#define TILE_R          15
#define TILE_P          16
#define TILE_C          17
#define TILE_O          18
#define TILE_L          19
#define TILE_V          20
#define TILE_D          21
#define TILE_COLON      22
#define TILE_EXCLAIM    23

// Number tiles (0-9)
#define TILE_NUM_0      24
#define TILE_NUM_1      25
#define TILE_NUM_2      26
#define TILE_NUM_3      27
#define TILE_NUM_4      28
#define TILE_NUM_5      29
#define TILE_NUM_6      30
#define TILE_NUM_7      31
#define TILE_NUM_8      32
#define TILE_NUM_9      33

// Maze dimensions (must be odd for maze gen algorithm)
#define MAZE_WIDTH      19      // @tunable range:11-31 step:2 desc:"Maze width in tiles (odd numbers only)"
#define MAZE_HEIGHT     17      // @tunable range:9-25 step:2 desc:"Maze height in tiles (odd numbers only)"

// Screen offset to center maze
#define MAZE_OFFSET_X   0
#define MAZE_OFFSET_Y   1

// Initialize tile data
void init_tiles(void);

#endif
