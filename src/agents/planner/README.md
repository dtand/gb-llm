# Planning Agent

The planning agent is a high-reasoning model that analyzes game descriptions and produces structured implementation plans for the coding agent.

## Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  User Request   │────▶│  Planning Agent │────▶│  Coding Agent   │
│  "Make a game"  │     │  (This Module)  │     │  (Copilot/etc)  │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Corpus Search  │
                        │  (manifest.json)│
                        └─────────────────┘
```

## Usage

```bash
python plan.py "A platformer where you collect coins and avoid enemies"
```

## Output

The planner outputs a JSON plan that includes:
- Required features identified from the description
- Relevant code samples from the corpus
- Ordered implementation steps
- Context references (file paths + line numbers)
