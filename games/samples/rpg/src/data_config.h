/**
 * @file    data_config.h
 * @brief   Configuration annotations for RPG data tables
 * @game    rpg
 * 
 * This file provides @config annotations that expose the data tables
 * for editing via the config API. The actual data structures are in
 * build/data.h (auto-generated from _schema.json).
 */

#ifndef DATA_CONFIG_H
#define DATA_CONFIG_H

// ============================================================
// HERO CONFIGURATION
// ============================================================

// @config table:heroes description:"Playable hero characters with stats"
// @field id uint8 auto description:"Unique hero ID"
// @field name string length:8 required description:"Hero name (8 chars max)"
// @field max_hp uint8 min:10 max:255 description:"Maximum hit points"
// @field max_mp uint8 min:0 max:99 description:"Maximum magic points"
// @field attack uint8 min:1 max:50 description:"Base attack power"
// @field defense uint8 min:0 max:50 description:"Base defense value"
// @field magic_dmg uint8 min:0 max:99 description:"Magic attack damage"

// ============================================================
// ENEMY CONFIGURATION
// ============================================================

// @config table:enemies description:"Enemy monsters to battle"
// @field id uint8 auto description:"Unique enemy ID"
// @field name string length:8 required description:"Enemy name (8 chars max)"
// @field max_hp uint8 min:5 max:200 description:"Maximum hit points"
// @field attack uint8 min:1 max:40 description:"Attack power"
// @field defense uint8 min:0 max:30 description:"Defense value"

#endif // DATA_CONFIG_H
