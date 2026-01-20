/**
 * @file    sprites.h
 * @brief   Sprite definitions for Bounce
 * @game    bounce
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// Animation frame tiles (4 frames)
#define TILE_BALL_0     0   // Small
#define TILE_BALL_1     1   // Medium
#define TILE_BALL_2     2   // Large
#define TILE_BALL_3     3   // Medium

// Sprite index
#define SPRITE_BALL     0

void sprites_init(void);

#endif
