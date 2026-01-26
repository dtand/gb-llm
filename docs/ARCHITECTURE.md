# GB Game Studio - Pipeline Architecture

> Comprehensive documentation of the Designer → Coder → Reviewer → Cleanup pipeline.

## Pipeline Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              GB-LLM PIPELINE OVERVIEW                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────────┐
                                    │     USER     │
                                    └──────┬───────┘
                                           │
                        ┌──────────────────┴──────────────────┐
                        ▼                                      ▼
              ┌─────────────────┐                    ┌─────────────────┐
              │  Chat Dialogue  │                    │  Build Feature  │
              │    (casual)     │                    │    (trigger)    │
              └────────┬────────┘                    └────────┬────────┘
                       │                                      │
                       ▼                                      │
              ┌─────────────────┐                             │
              │  Conversation   │◄────────────────────────────┘
              │    History      │
              │ (conversation   │
              │    .json)       │
              └────────┬────────┘
                       │
                       │ find last "build_feature_complete" marker
                       │ only use conversation AFTER that point
                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                PIPELINE EXECUTION                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 1: DESIGNER                                    (claude-opus-4)        │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                              │    │
│  │  INPUTS:                           OUTPUTS:                                  │    │
│  │  ┌──────────────────┐              ┌─────────────────────────────────┐      │    │
│  │  │ summary.json     │───────────►  │  ContextPackage:                │      │    │
│  │  │ - features.added │              │   - feature_gaps[]              │      │    │
│  │  │ - patterns       │              │   - modifications[]             │      │    │
│  │  │ - files/funcs    │              │   - corpus_examples[]           │      │    │
│  │  └──────────────────┘              │   - existing_features           │      │    │
│  │  ┌──────────────────┐              │   - known_issues                │      │    │
│  │  │ user_request     │───────────►  └─────────────────────────────────┘      │    │
│  │  │ (synthesized     │                                                        │    │
│  │  │  from chat)      │                                                        │    │
│  │  └──────────────────┘              Gap Analysis:                             │    │
│  │  ┌──────────────────┐               • NEW features → feature_gaps            │    │
│  │  │ Vector DB        │───────────►   • FIX/TUNE existing → modifications      │    │
│  │  │ (corpus search)  │                                                        │    │
│  │  └──────────────────┘                                                        │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                         │                                            │
│                    if no gaps AND no modifications → return "nothing to do"          │
│                                         │                                            │
│                                         ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 2: SNAPSHOT                                                           │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │  💾 Create backup of src/ files for rollback on failure                     │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                         │                                            │
│                                         ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 3: CODER                                       (claude-sonnet-4)      │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                              │    │
│  │  INPUTS:                           OUTPUTS:                                  │    │
│  │  ┌──────────────────┐              ┌─────────────────────────────────┐      │    │
│  │  │ ContextPackage   │───────────►  │  CoderResult:                   │      │    │
│  │  │ + full source    │              │   - files_changed[]             │      │    │
│  │  │   files          │              │   - changes_made[]              │      │    │
│  │  │ + CODE_STANDARDS │              │   - features_implemented[]      │      │    │
│  │  └──────────────────┘              │   - build_success               │      │    │
│  │  ┌──────────────────┐              └─────────────────────────────────┘      │    │
│  │  │ reviewer_feedback│                                                        │    │
│  │  │ (on retry only)  │              Actions:                                  │    │
│  │  └──────────────────┘               • Writes modified files to disk          │    │
│  │                                      • Runs `make` to compile                 │    │
│  │                                      • Adds @tunable annotations              │    │
│  │                                                                              │    │
│  │  On build failure → rollback to snapshot                                     │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                         │                                            │
│                                         ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 4: REVIEWER (optional, up to 3 retries)        (claude-sonnet-4)      │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                              │    │
│  │  INPUTS:                           OUTPUTS:                                  │    │
│  │  ┌──────────────────┐              ┌─────────────────────────────────┐      │    │
│  │  │ before_files     │───────────►  │  ReviewResult:                  │      │    │
│  │  │ after_files      │              │   - approved: bool              │      │    │
│  │  │ (diff)           │              │   - issues[]                    │      │    │
│  │  └──────────────────┘              │   - critical_count              │      │    │
│  │                                    │   - warning_count               │      │    │
│  │  Checks:                           └────────────┬────────────────────┘      │    │
│  │   • GBDK compilation errors                     │                            │    │
│  │   • Sprite limit violations                     │                            │    │
│  │   • Memory issues                     ┌─────────┴─────────┐                  │    │
│  │   • Logic bugs                        │                   │                  │    │
│  │                                       ▼                   ▼                  │    │
│  │                              critical issues?     approved ✓                 │    │
│  │                                       │                   │                  │    │
│  │                                       ▼                   │                  │    │
│  │                              ┌────────────────┐           │                  │    │
│  │                              │ retry < 3?     │           │                  │    │
│  │                              └───────┬────────┘           │                  │    │
│  │                                yes   │    no              │                  │    │
│  │                                ▼     │    ▼               │                  │    │
│  │                  ┌─────────────────┐ │  proceed           │                  │    │
│  │                  │ Send feedback   │ │  with issues       │                  │    │
│  │                  │ back to CODER   │─┘                    │                  │    │
│  │                  │ (loop to Ph.3)  │                      │                  │    │
│  │                  └─────────────────┘                      │                  │    │
│  └─────────────────────────────────────────────────────┬─────┘──────────────────┘    │
│                                                        │                             │
│                                                        ▼                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 5: CLEANUP (optional, disabled by default)    (claude-sonnet-4)       │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                              │    │
│  │  • Removes code duplication                                                  │    │
│  │  • Extracts magic numbers to constants                                       │    │
│  │  • Splits large files (>300 lines) into modules                             │    │
│  │  • NEVER splits asset files (sprites.c, tiles.c, etc.)                      │    │
│  │  • Updates Makefile when creating new files                                  │    │
│  │                                                                              │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                         │                                            │
│                                         ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 6: UPDATE PROJECT STATE                                               │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                              │    │
│  │  ✓ Update project status ("compiled" or "build_failed")                     │    │
│  │  ✓ Regenerate summary.json (parse files, detect patterns)                   │    │
│  │  ✓ Append features to summary.features.added                                │    │
│  │  ✓ Record in conversation with "build_feature_complete" marker              │    │
│  │                                                                              │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
                              ┌─────────────────┐
                              │ PipelineResult  │
                              │ - success       │
                              │ - features[]    │
                              │ - files[]       │
                              │ - build_success │
                              └─────────────────┘
```

---

## Entry Points

### Chat Dialogue (`chat()` method)

Casual conversation between user and Designer agent for ideation and planning.

- Stores turns in `conversation.json`
- No code changes - just discussing features
- User describes what they want in natural language

### Build Feature (`build_from_conversation()` method)

Triggered by user clicking "Build Feature" button in the UI.

1. Finds the last `build_feature_complete` marker in conversation
2. Only processes messages **after** that point (prevents re-building old features)
3. Synthesizes the relevant conversation into a formal feature request
4. Calls `run()` with the synthesized request

---

## Agent Components

### 1. Designer Agent

**Location:** `src/agents/designer/__init__.py`

**Model:** `claude-opus-4` (configurable)

**Purpose:** Gap analysis - figures out what needs to change

**Inputs:**
| Input | Source |
|-------|--------|
| Project summary | `context/summary.json` |
| User request | Synthesized from conversation |
| Corpus examples | Vector DB search |

**Outputs:** `ContextPackage` containing:

```python
@dataclass
class ContextPackage:
    project_id: str
    project_name: str
    current_state: str
    existing_files: list[dict]
    existing_features: list[str]
    existing_patterns: list[str]
    user_request: str
    feature_gaps: list[FeatureGap]      # NEW features to add
    modifications: list[Modification]    # Changes to EXISTING features
    corpus_examples: list[dict]
    known_issues: list[str]
    constraints: list[str]
```

**Key Behaviors:**
- Strictly focused on user's EXACT request (won't suggest extras)
- Distinguishes between "add new" (`feature_gaps`) vs "fix existing" (`modifications`)
- Queries vector DB only for net-new patterns

---

### 2. Coder Agent

**Location:** `src/agents/coder/coder_v2.py`

**Model:** `claude-sonnet-4` (configurable)

**Purpose:** Writes the actual code

**Inputs:**
| Input | Source |
|-------|--------|
| ContextPackage | From Designer |
| Full source files | Read from disk |
| CODE_STANDARDS.md | Style guide |
| Reviewer feedback | On retry only |

**Outputs:** `CoderResult`

```python
@dataclass
class CoderResult:
    success: bool
    files_changed: list[FileChange]
    changes_made: list[str]
    features_implemented: list[str]
    build_success: bool
    error: Optional[str]
```

**Key Behaviors:**
- Outputs **complete file contents** (not diffs)
- Runs `make` after writing files
- Adds `@tunable` annotations for gameplay values
- Preserves existing code not related to the change

---

### 3. Reviewer Agent

**Location:** `src/agents/reviewer/code_reviewer.py`

**Model:** `claude-sonnet-4` (configurable)

**Purpose:** Quality gate - catches bugs before they ship

**Inputs:**
| Input | Description |
|-------|-------------|
| before_files | File contents before Coder ran |
| after_files | File contents after Coder ran |
| task_description | What was being implemented |

**Outputs:** `ReviewResult`

```python
@dataclass
class ReviewResult:
    approved: bool
    issues: list[ReviewIssue]
    critical_count: int
    warning_count: int
```

**Checks:**
- GBDK compilation constraints
- Sprite limit violations (40 max)
- Memory issues (8KB WRAM)
- Logic bugs
- Code quality issues

**Retry Loop:**
- Up to 3 retries on critical issues
- Sends structured feedback back to Coder
- After 3 failures, proceeds with warnings logged

---

### 4. Cleanup Agent

**Location:** `src/agents/cleanup/cleanup_agent.py`

**Model:** `claude-sonnet-4` (configurable)

**Purpose:** Improve code quality without changing functionality

**Enabled:** Off by default (per-project opt-in via `agent_config`)

**Actions:**
- Extract magic numbers to `#define` constants
- Remove code duplication
- Split large files (>300 lines) into modules
- Update Makefile when creating new `.c` files

**Protected Files (NEVER split):**
- `sprites.c` / `sprites.h`
- `tiles.c` / `tiles.h`
- `maps.c` / `maps.h`
- `sounds.c` / `sounds.h`

These asset files are parsed by UI tools for visualization.

---

## Project State Management

### File Structure

```
games/projects/{project-id}/
├── metadata.json           # Project config, status, agent settings
├── Makefile               # Build configuration
├── context/
│   ├── summary.json       # Parsed code structure, features, patterns
│   └── conversation.json  # Full chat history with metadata
├── src/
│   ├── main.c
│   ├── game.h
│   ├── game.c
│   ├── sprites.h
│   └── sprites.c
├── build/
│   └── {name}.gb          # Compiled ROM
└── snapshots/             # Rollback points
```

### Key Files

| File | Purpose |
|------|---------|
| `metadata.json` | Project name, status, ROM path, agent_config |
| `summary.json` | Parsed code structure, features, patterns |
| `conversation.json` | Full chat history with turn metadata |

### Feature Tracking

```json
{
  "features": {
    "from_template": ["sprites", "scrolling", "collision"],
    "added": ["double_jump", "coin_system", "ui_display"],
    "planned": []
  }
}
```

- `from_template` - Features inherited from forked template
- `added` - Features implemented via pipeline (updated on success)
- `planned` - Reserved for future use

### Conversation Boundaries

The `build_feature_complete` metadata marker separates design sessions:

```json
{
  "role": "assistant",
  "content": "✅ Done! I implemented...",
  "metadata": {
    "type": "build_feature_complete",
    "features": ["ui_display"],
    "files": ["src/game.c", "src/game.h"]
  }
}
```

When "Build Feature" is clicked, only conversation **after** the last such marker is processed.

---

## Tunable Parameters System

### Annotation Format

```c
// @tunable category range:MIN-MAX Description
#define CONSTANT_NAME value
```

### Categories

| Category | What to include |
|----------|-----------------|
| `player` | Movement speeds, jump strength, lives, health |
| `physics` | Gravity, friction, acceleration, bounce factors |
| `difficulty` | Enemy speeds, spawn rates, max enemies |
| `timing` | Animation delays, invincibility frames, cooldowns |
| `scoring` | Points per action, bonuses, multipliers |
| `enemies` | Patrol ranges, attack speeds, damage amounts |

### Example

```c
// @tunable player range:1-4 Horizontal movement speed
#define PLAYER_SPEED 2

// @tunable physics range:1-3 Gravity acceleration per frame
#define GRAVITY 1

// @tunable difficulty range:60-180 Frames between enemy spawns
#define SPAWN_RATE 90
```

### UI Features

- Sliders grouped by category
- Direct number input alongside sliders
- Change tracking with visual indicators
- "Apply & Rebuild" button compiles with new values
- "Reset" button reverts to original values

**Purpose:** Let users tweak gameplay without re-running AI.

---

## Agent Configuration

Each project can configure agents via `metadata.json`:

```json
{
  "agent_config": {
    "cleanup": {
      "enabled": true,
      "model": "claude-haiku-3-5-20241022"
    }
  }
}
```

The "Agents" tab in the workspace UI allows toggling and model selection per-agent.

### Available Models

| Model ID | Use Case |
|----------|----------|
| `claude-opus-4-20250514` | Designer (complex analysis) |
| `claude-sonnet-4-20250514` | Coder, Reviewer, Cleanup |
| `claude-haiku-3-5-20241022` | Fast/cheap tasks |

---

## API Endpoints

### Pipeline Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v2/projects/{id}/chat` | POST | Send chat message |
| `/api/v2/projects/{id}/build` | POST | Trigger build from conversation |
| `/ws/projects/{id}` | WebSocket | Real-time pipeline progress |

### Project Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v2/projects` | GET | List all projects |
| `/api/v2/projects` | POST | Create new project |
| `/api/v2/projects/{id}` | GET | Get project details |
| `/api/v2/projects/{id}/files` | GET | List source files |
| `/api/v2/projects/{id}/file` | GET/PUT | Read/write file |

### Specialized

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v2/projects/{id}/sprites` | GET | Parse sprites from sprites.c |
| `/api/v2/projects/{id}/tuning` | GET/PUT | Read/update tunable parameters |
| `/api/v2/projects/{id}/snapshots` | GET/POST | Manage rollback points |

---

## Error Handling

### Build Failures

1. Coder writes files and runs `make`
2. If `make` fails, error is captured
3. Pipeline attempts to fix (up to 3 retries with Reviewer feedback)
4. On persistent failure, rollback to pre-change snapshot
5. Error recorded in conversation and returned to user

### Rollback System

Before any code changes:
1. Snapshot of all `src/` files is created
2. Snapshot ID stored for the pipeline run
3. On failure, files restored from snapshot
4. Snapshots can also be triggered manually via UI

---

## Vector Database (Corpus)

### Purpose

Provides reference implementations from sample games for the Coder.

### Structure

```
games/corpus_db/
├── index_metadata.json
├── functions/
│   ├── documents.json
│   └── embeddings.npy
├── constants/
│   ├── documents.json
│   └── embeddings.npy
├── sprites/
│   └── ...
└── structs/
    └── ...
```

### Usage

1. Designer identifies feature gaps
2. Each gap has `corpus_queries` (e.g., "jump physics", "coin collection")
3. Vector search finds relevant code from sample games
4. Top matches included in ContextPackage for Coder

### Sample Games

Located in `games/samples/`:
- `bounce/`, `breakout/`, `platformer/`, `pong/`, `runner/`
- `shooter/`, `snake/`, `puzzle/`, `rpg/`, etc.

Each provides reference patterns for common game mechanics.
