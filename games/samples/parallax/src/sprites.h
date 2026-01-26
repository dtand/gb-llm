/**
 * @file    sprites.h
 * @brief   Tile declarations for Parallax Scroller
 * @game    parallax
 */

#ifndef SPRITES_H
#define SPRITES_H

#include <gb/gb.h>
#include <stdint.h>

// ============================================================
// BACKGROUND TILE INDICES
// ============================================================

#define TILE_SKY        0   // Light/empty sky
#define TILE_MOUNTAIN   1   // Dark mountain silhouette
#define TILE_HILLS      2   // Medium hills
#define TILE_GRASS      3   // Grass top
#define TILE_GROUND     4   // Dirt/ground fill
#define TILE_ROCK       5   // Rock marker on ground
#define TILE_TREE       6   // Tree marker

// ============================================================
// FUNCTIONS
// ============================================================

void sprites_init(void);

#endif
