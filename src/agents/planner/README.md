# Planning Agent

LLM-powered planning agent that uses Claude to analyze game descriptions and produce structured implementation plans.

## Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  User Request   │────▶│  Planning Agent │────▶│  Coding Agent   │
│  "Make a game"  │     │  (Claude Opus)  │     │  (Executes Plan)│
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Corpus Context │
                        │  (manifest.json)│
                        └─────────────────┘
```

## Setup

```bash
cd src/agents/planner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
```

## Usage

```bash
# Default (Sonnet - faster, cheaper)
python llm_planner.py "A platformer where you collect coins and avoid enemies"

# Opus (maximum reasoning)
python llm_planner.py "A complex RPG with inventory" -m claude-opus-4-20250514

# Verbose mode
python llm_planner.py "A space shooter" -v

# Output to file
python llm_planner.py "A puzzle game" -o plan.json -f json
```

## How It Works

1. **Corpus Context**: Builds context from `manifest.json` listing all samples and their features
2. **Claude Reasoning**: Sends game description + corpus context to Claude
3. **Plan Generation**: Claude analyzes requirements and creates ordered implementation steps
4. **Code References**: Attaches relevant code snippets from corpus samples to each step

## Output

The planner outputs a structured plan with:
- **Game type** detected from description
- **Required features** identified by Claude
- **Relevant samples** from the corpus
- **Implementation steps** with:
  - Dependencies between steps
  - Code references from working samples
  - Acceptance criteria
  - Complexity estimates
