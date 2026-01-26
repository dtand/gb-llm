#include <gb/gb.h>
#include <string.h>
#include "game.h"
#include "sprites.h"

GameState game;

// Stack for recursive backtracker maze generation
static uint8_t stack_x[128];
static uint8_t stack_y[128];
static uint8_t stack_top;

// Simple LCG random number generator
static uint16_t rand_state;

static uint16_t random(void) {
    rand_state = rand_state * 1103515245 + 12345;
    return (rand_state >> 8) & 0x7FFF;
}

static void seed_random(uint16_t seed) {
    rand_state = seed;
}

// Shuffle directions array
static void shuffle_directions(uint8_t* dirs) {
    for (uint8_t i = 3; i > 0; i--) {
        uint8_t j = random() % (i + 1);
        uint8_t temp = dirs[i];
        dirs[i] = dirs[j];
        dirs[j] = temp;
    }
}

// Check if a cell is valid and unvisited
static uint8_t is_valid_unvisited(int8_t x, int8_t y) {
    if (x < 0 || x >= MAZE_WIDTH || y < 0 || y >= MAZE_HEIGHT) {
        return 0;
    }
    return game.maze[x][y] == CELL_WALL;
}

// Count visited neighbors (for checking if we should carve)
static uint8_t count_path_neighbors(uint8_t x, uint8_t y) {
    uint8_t count = 0;
    if (x > 0 && game.maze[x-1][y] == CELL_PATH) count++;
    if (x < MAZE_WIDTH-1 && game.maze[x+1][y] == CELL_PATH) count++;
    if (y > 0 && game.maze[x][y-1] == CELL_PATH) count++;
    if (y < MAZE_HEIGHT-1 && game.maze[x][y+1] == CELL_PATH) count++;
    return count;
}

// Recursive backtracker maze generation
void generate_maze(void) {
    // Initialize all cells as walls
    for (uint8_t x = 0; x < MAZE_WIDTH; x++) {
        for (uint8_t y = 0; y < MAZE_HEIGHT; y++) {
            game.maze[x][y] = CELL_WALL;
        }
    }
    
    // Start from position (1,1) - odd coordinates for proper maze
    uint8_t start_x = 1;
    uint8_t start_y = 1;
    
    game.maze[start_x][start_y] = CELL_PATH;
    
    // Push starting cell to stack
    stack_top = 0;
    stack_x[stack_top] = start_x;
    stack_y[stack_top] = start_y;
    stack_top++;
    
    // Direction offsets (move by 2 cells at a time for proper maze structure)
    const int8_t dx[] = {0, 2, 0, -2};  // up, right, down, left
    const int8_t dy[] = {-2, 0, 2, 0};
    
    while (stack_top > 0) {
        // Get current cell
        uint8_t cx = stack_x[stack_top - 1];
        uint8_t cy = stack_y[stack_top - 1];
        
        // Find unvisited neighbors
        uint8_t dirs[4] = {0, 1, 2, 3};
        shuffle_directions(dirs);
        
        uint8_t found = 0;
        for (uint8_t i = 0; i < 4; i++) {
            uint8_t d = dirs[i];
            int8_t nx = cx + dx[d];
            int8_t ny = cy + dy[d];
            
            // Check if neighbor is valid and unvisited
            if (nx > 0 && nx < MAZE_WIDTH-1 && ny > 0 && ny < MAZE_HEIGHT-1) {
                if (game.maze[nx][ny] == CELL_WALL) {
                    // Carve path to neighbor (both the wall between and the cell)
                    game.maze[cx + dx[d]/2][cy + dy[d]/2] = CELL_PATH;
                    game.maze[nx][ny] = CELL_PATH;
                    
                    // Push neighbor to stack
                    stack_x[stack_top] = nx;
                    stack_y[stack_top] = ny;
                    stack_top++;
                    
                    found = 1;
                    break;
                }
            }
        }
        
        // If no unvisited neighbors, backtrack
        if (!found) {
            stack_top--;
        }
    }
    
    // Set player start position (top-left area)
    game.player_x = 1;
    game.player_y = 1;
    
    // Set exit position (bottom-right area)
    // Find a valid path cell near bottom-right
    game.exit_x = MAZE_WIDTH - 2;
    game.exit_y = MAZE_HEIGHT - 2;
    
    // Make sure exit is on a path (search for nearest path cell)
    if (game.maze[game.exit_x][game.exit_y] != CELL_PATH) {
        for (int8_t ox = 0; ox >= -4; ox--) {
            for (int8_t oy = 0; oy >= -4; oy--) {
                uint8_t tx = game.exit_x + ox;
                uint8_t ty = game.exit_y + oy;
                if (tx > 0 && ty > 0 && game.maze[tx][ty] == CELL_PATH) {
                    game.exit_x = tx;
                    game.exit_y = ty;
                    goto found_exit;
                }
            }
        }
    }
    found_exit:;
}

void draw_maze(void) {
    // Clear entire background first
    for (uint8_t y = 0; y < 18; y++) {
        for (uint8_t x = 0; x < 20; x++) {
            set_bkg_tile_xy(x, y, TILE_EMPTY);
        }
    }
    
    // Draw maze tiles
    for (uint8_t y = 0; y < MAZE_HEIGHT; y++) {
        for (uint8_t x = 0; x < MAZE_WIDTH; x++) {
            uint8_t tile;
            if (x == game.exit_x && y == game.exit_y) {
                tile = TILE_EXIT;
            } else if (game.maze[x][y] == CELL_WALL) {
                tile = TILE_WALL;
            } else {
                tile = TILE_FLOOR;
            }
            set_bkg_tile_xy(x + MAZE_OFFSET_X, y + MAZE_OFFSET_Y, tile);
        }
    }
}

void draw_player(void) {
    // Draw player tile at current position
    set_bkg_tile_xy(game.player_x + MAZE_OFFSET_X, 
                    game.player_y + MAZE_OFFSET_Y, 
                    TILE_PLAYER);
}

void erase_player(void) {
    // Replace player tile with visited breadcrumb
    set_bkg_tile_xy(game.player_x + MAZE_OFFSET_X, 
                    game.player_y + MAZE_OFFSET_Y, 
                    TILE_VISITED);
}

void draw_hud(void) {
    // Draw level indicator on row 0: "LV:X"
    set_bkg_tile_xy(0, 0, TILE_L);
    set_bkg_tile_xy(1, 0, TILE_V);
    set_bkg_tile_xy(2, 0, TILE_COLON);
    set_bkg_tile_xy(3, 0, TILE_NUM_0 + game.level);
    
    // Draw moves counter: "M:XXX"
    set_bkg_tile_xy(14, 0, TILE_M);
    set_bkg_tile_xy(15, 0, TILE_COLON);
    
    uint16_t m = game.moves;
    set_bkg_tile_xy(18, 0, TILE_NUM_0 + (m % 10));
    m /= 10;
    set_bkg_tile_xy(17, 0, TILE_NUM_0 + (m % 10));
    m /= 10;
    set_bkg_tile_xy(16, 0, TILE_NUM_0 + (m % 10));
}

void draw_title(void) {
    // Clear screen
    for (uint8_t y = 0; y < 18; y++) {
        for (uint8_t x = 0; x < 20; x++) {
            set_bkg_tile_xy(x, y, TILE_EMPTY);
        }
    }
    
    // Draw "MAZE" centered
    set_bkg_tile_xy(8, 6, TILE_M);
    set_bkg_tile_xy(9, 6, TILE_A);
    set_bkg_tile_xy(10, 6, TILE_Z);
    set_bkg_tile_xy(11, 6, TILE_E);
    
    // Draw "PRESS START"
    set_bkg_tile_xy(5, 10, TILE_P);
    set_bkg_tile_xy(6, 10, TILE_R);
    set_bkg_tile_xy(7, 10, TILE_E);
    set_bkg_tile_xy(8, 10, TILE_S);
    set_bkg_tile_xy(9, 10, TILE_S);
    set_bkg_tile_xy(11, 10, TILE_S);
    set_bkg_tile_xy(12, 10, TILE_T);
    set_bkg_tile_xy(13, 10, TILE_A);
    set_bkg_tile_xy(14, 10, TILE_R);
    set_bkg_tile_xy(15, 10, TILE_T);
}

void draw_win(void) {
    // Draw "WIN!" on screen
    set_bkg_tile_xy(8, 8, TILE_W);
    set_bkg_tile_xy(9, 8, TILE_I);
    set_bkg_tile_xy(10, 8, TILE_N);
    set_bkg_tile_xy(11, 8, TILE_EXCLAIM);
}

void move_player(int8_t dx, int8_t dy) {
    uint8_t new_x = game.player_x + dx;
    uint8_t new_y = game.player_y + dy;
    
    // Check bounds
    if (new_x >= MAZE_WIDTH || new_y >= MAZE_HEIGHT) {
        return;
    }
    
    // Check if destination is a path (not a wall)
    if (game.maze[new_x][new_y] == CELL_PATH) {
        // Erase player at old position (leave breadcrumb)
        erase_player();
        
        // Update position
        game.player_x = new_x;
        game.player_y = new_y;
        game.moves++;
        
        // Draw player at new position
        draw_player();
        
        // Update move counter in HUD
        draw_hud();
        
        // Check if reached exit
        if (game.player_x == game.exit_x && game.player_y == game.exit_y) {
            game.state = STATE_WIN;
            draw_win();
        }
    }
}

void game_init(void) {
    game.state = STATE_TITLE;
    game.level = 1;
    game.moves = 0;
    game.seed = 12345;  // Initial seed
    game.joypad_prev = 0;
    
    draw_title();
}

void start_level(void) {
    game.moves = 0;
    
    // Seed random with level-based seed for reproducible mazes
    seed_random(game.seed + game.level * 1000);
    
    game.state = STATE_GENERATING;
    generate_maze();
    draw_maze();
    draw_player();
    draw_hud();
    
    game.state = STATE_PLAYING;
}

void game_update(void) {
    uint8_t joy = joypad();
    uint8_t joy_pressed = joy & ~game.joypad_prev;
    
    switch (game.state) {
        case STATE_TITLE:
            // Increment seed while on title (pseudo-random based on timing)
            game.seed++;
            
            if (joy_pressed & J_START) {
                game.level = 1;
                start_level();
            }
            break;
            
        case STATE_PLAYING:
            // D-pad movement (only on press, not hold)
            if (joy_pressed & J_UP) {
                move_player(0, -1);
            }
            if (joy_pressed & J_DOWN) {
                move_player(0, 1);
            }
            if (joy_pressed & J_LEFT) {
                move_player(-1, 0);
            }
            if (joy_pressed & J_RIGHT) {
                move_player(1, 0);
            }
            break;
            
        case STATE_WIN:
            // Wait for button press to continue to next level
            if (joy_pressed & (J_START | J_A)) {
                game.level++;
                if (game.level > 9) {
                    game.level = 1;  // Wrap around
                }
                start_level();
            }
            break;
    }
    
    game.joypad_prev = joy;
}
