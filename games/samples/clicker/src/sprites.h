/**
 * @file    sprites.h
 * @brief   Tile definitions for Clicker
 * @game    clicker
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// Digit tiles (0-9)
#define TILE_DIGIT_0    0
#define TILE_DIGIT_1    1
#define TILE_DIGIT_2    2
#define TILE_DIGIT_3    3
#define TILE_DIGIT_4    4
#define TILE_DIGIT_5    5
#define TILE_DIGIT_6    6
#define TILE_DIGIT_7    7
#define TILE_DIGIT_8    8
#define TILE_DIGIT_9    9

// Blank tile for clearing screen
#define TILE_BLANK      20

// Letter tiles for labels
#define TILE_C          10
#define TILE_O          11
#define TILE_U          12
#define TILE_N          13
#define TILE_T          14
#define TILE_H          15
#define TILE_I          16
#define TILE_G          17

void sprites_init(void);

#endif
