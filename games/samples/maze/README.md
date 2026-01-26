# Maze Explorer

A procedural maze generation demo showcasing the recursive backtracker algorithm.

## Features

- **Procedural Generation**: Each level generates a unique maze using recursive backtracker
- **Perfect Mazes**: Every maze has exactly one solution path
- **Breadcrumb Trail**: Visited cells show dots to help track your path
- **Multiple Levels**: Complete a maze to advance to the next level
- **Move Counter**: Track how many moves you take to solve each maze

## Controls

- **D-Pad**: Move through the maze
- **START**: Begin game / Start next level
- **A**: Start next level (after winning)

## Technical Highlights

### Recursive Backtracker Algorithm
The maze is generated using the recursive backtracker (depth-first search) algorithm:
1. Start from a cell, mark it as visited
2. Randomly choose an unvisited neighbor
3. Remove the wall between current cell and chosen neighbor
4. Move to the chosen neighbor and repeat
5. If no unvisited neighbors, backtrack to previous cell
6. Continue until all cells are visited

This creates "perfect" mazes with:
- Exactly one path between any two points
- No loops or isolated sections
- High-quality winding passages

### Grid Structure
- Maze uses odd dimensions (19x17) for proper wall structure
- Cells alternate between walls and paths
- Movement carves through walls 2 cells at a time

### Memory Efficiency
- Maze stored as single-byte cells (wall/path)
- Stack-based generation avoids recursion limits
- Minimal RAM footprint (~400 bytes for maze array)

## Code Patterns Demonstrated

1. **Procedural Generation**: Creating content algorithmically
2. **Stack-based DFS**: Non-recursive maze generation
3. **LCG Random Numbers**: Simple pseudo-random number generator
4. **Array Shuffling**: Fisher-Yates shuffle for random directions
5. **Grid Navigation**: Tile-based movement with collision
6. **Breadcrumb System**: Visual path tracking

## Building

```bash
make clean && make
```

## File Structure

```
maze/
├── Makefile
├── metadata.json
├── README.md
├── build/
│   └── maze.gb
└── src/
    ├── main.c      # Entry point and game loop
    ├── game.h      # Game state and declarations
    ├── game.c      # Maze generation and gameplay
    ├── sprites.h   # Tile definitions
    └── sprites.c   # Tile graphics data
```
