# Data System Specification

This document defines the schema-driven data system for managing game content (characters, items, enemies, levels, etc.) that gets compiled into ROM.

## Overview

```
_schema.json          →  Defines table structures
data/*.json           →  Contains content instances  
build/data.c, data.h  →  Auto-generated C code
```

The **Designer** agent decides what tables/fields exist. The **Generator** (build script) converts JSON to C. The **Coder** uses the generated headers.

---

## Schema Format (`_schema.json`)

```json
{
  "version": 1,
  "tables": {
    "characters": {
      "description": "Playable and NPC characters",
      "fields": {
        "id": {
          "type": "uint8",
          "auto": true,
          "description": "Unique identifier (auto-assigned)"
        },
        "name": {
          "type": "string",
          "length": 12,
          "required": true,
          "description": "Display name"
        },
        "hp": {
          "type": "uint8",
          "min": 1,
          "max": 255,
          "default": 10,
          "description": "Hit points"
        },
        "weapon_id": {
          "type": "ref",
          "target": "items",
          "nullable": true,
          "description": "Equipped weapon"
        },
        "element": {
          "type": "enum",
          "values": ["none", "fire", "water", "earth", "wind"],
          "default": "none",
          "description": "Elemental affinity"
        },
        "is_playable": {
          "type": "bool",
          "default": false,
          "description": "Can player control this character?"
        }
      }
    }
  }
}
```

---

## Field Types

| Type | C Type | Size | Validation |
|------|--------|------|------------|
| `uint8` | `uint8_t` | 1 byte | `min`, `max` |
| `int8` | `int8_t` | 1 byte | `min`, `max` |
| `uint16` | `uint16_t` | 2 bytes | `min`, `max` |
| `int16` | `int16_t` | 2 bytes | `min`, `max` |
| `bool` | `uint8_t` | 1 byte | — |
| `string` | `char[N]` | N bytes | `length` (required) |
| `enum` | `uint8_t` | 1 byte | `values` (required) |
| `ref` | `uint8_t` | 1 byte | `target` (required), `nullable` |

---

## Field Properties

| Property | Required | Description |
|----------|----------|-------------|
| `type` | ✓ | One of the types above |
| `description` | | Human-readable description |
| `required` | | If true, cannot be null/empty |
| `default` | | Default value for new rows |
| `auto` | | Auto-assign sequential ID (for `id` fields) |
| `min` | | Minimum value (numeric types) |
| `max` | | Maximum value (numeric types) |
| `length` | | Max characters (string type, required) |
| `values` | | Allowed values (enum type, required) |
| `target` | | Target table name (ref type, required) |
| `nullable` | | If true, ref can be 0/null |

---

## Data Files (`data/*.json`)

Each table gets its own JSON file:

**`data/characters.json`**
```json
[
  {
    "id": 1,
    "name": "Hero",
    "hp": 20,
    "weapon_id": 1,
    "element": "fire",
    "is_playable": true
  },
  {
    "id": 2,
    "name": "Goblin",
    "hp": 5,
    "weapon_id": null,
    "element": "none",
    "is_playable": false
  }
]
```

---

## Generated C Code

**`build/data.h`**
```c
#ifndef DATA_H
#define DATA_H

#include <gb/gb.h>

// Enums
typedef enum {
    ELEMENT_NONE = 0,
    ELEMENT_FIRE = 1,
    ELEMENT_WATER = 2,
    ELEMENT_EARTH = 3,
    ELEMENT_WIND = 4
} Element;

// Structs
typedef struct {
    uint8_t id;
    char name[12];
    uint8_t hp;
    uint8_t weapon_id;
    Element element;
    uint8_t is_playable;
} Character;

// Table info
#define CHARACTER_COUNT 2

// Accessors
extern const Character characters[];
const Character* get_character(uint8_t id);

#endif
```

**`build/data.c`**
```c
#include "data.h"

const Character characters[] = {
    {1, "Hero", 20, 1, ELEMENT_FIRE, 1},
    {2, "Goblin", 5, 0, ELEMENT_NONE, 0}
};

const Character* get_character(uint8_t id) {
    for (uint8_t i = 0; i < CHARACTER_COUNT; i++) {
        if (characters[i].id == id) return &characters[i];
    }
    return NULL;
}
```

---

## ROM Budget

The generator tracks memory usage:

**`build/rom_budget.json`**
```json
{
  "total_bytes": 156,
  "bank_limit": 16384,
  "usage_percent": 0.95,
  "tables": {
    "characters": {
      "row_size": 17,
      "row_count": 2,
      "total_bytes": 34
    },
    "items": {
      "row_size": 14,
      "row_count": 8,
      "total_bytes": 112
    }
  }
}
```

### Budget Limits
- **Warning**: 80% of bank (13,107 bytes)
- **Error**: 100% of bank (16,384 bytes)

---

## Designer Schema Changes

The Designer outputs schema changes in its response:

```json
{
  "feature_gaps": [...],
  "modifications": [...],
  "schema_changes": {
    "add_tables": [
      {
        "name": "enemies",
        "description": "Enemy types in the game",
        "fields": {
          "id": {"type": "uint8", "auto": true},
          "name": {"type": "string", "length": 10},
          "hp": {"type": "uint8", "default": 5}
        }
      }
    ],
    "add_fields": [
      {
        "table": "characters",
        "name": "level",
        "field": {"type": "uint8", "min": 1, "max": 99, "default": 1}
      }
    ],
    "remove_tables": [],
    "remove_fields": []
  }
}
```

---

## When to Use Data vs @tunable

| Use Case | Solution |
|----------|----------|
| Game-wide constant (gravity, speed) | `@tunable` in game.h |
| Collection of similar items | Data table |
| Single global setting | `@tunable` |
| Multiple instances with same structure | Data table |

**Rule of thumb**: 
- `@tunable` = "How the game feels" (sliders)
- Data tables = "What exists in the game" (spreadsheets)

---

## File Locations

```
project/
├── _schema.json           # Table definitions
├── data/
│   ├── characters.json    # Character instances
│   ├── items.json         # Item instances
│   └── enemies.json       # Enemy instances
├── build/
│   ├── data.h             # Generated header
│   ├── data.c             # Generated source
│   └── rom_budget.json    # Memory usage report
└── src/
    └── main.c             # #include "../build/data.h"
```
