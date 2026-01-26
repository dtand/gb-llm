"""
Project context schemas.

Defines the data structures for project summaries - the JSON-based
context that agents use to understand a project's current state.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
import json


@dataclass
class FunctionInfo:
    """Information about a function in a source file."""
    name: str
    return_type: str
    parameters: list[str]
    description: str = ""
    line_start: int = 0
    line_end: int = 0


@dataclass
class StructInfo:
    """Information about a struct/typedef in a source file."""
    name: str
    fields: list[dict]  # [{name, type, comment}]
    description: str = ""
    line_start: int = 0
    line_end: int = 0


@dataclass
class ConstantInfo:
    """Information about a #define constant."""
    name: str
    value: str
    comment: str = ""


@dataclass
class FileInfo:
    """Information about a source file in the project."""
    path: str
    description: str
    structs: list[StructInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    constants: list[ConstantInfo] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    lines: int = 0


@dataclass
class KnownIssue:
    """A known issue or bug in the project."""
    description: str
    severity: str  # "critical", "major", "minor"
    source: str  # "human_feedback", "build_error", "runtime"
    timestamp: str
    resolved: bool = False


@dataclass
class FeatureSet:
    """Features in the project, split by origin."""
    from_template: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    planned: list[str] = field(default_factory=list)


@dataclass
class ProjectSummary:
    """
    Complete summary of a project's current state.
    
    This is the primary context document that agents read to understand
    what a project contains before making modifications.
    """
    # Identity
    project_id: str
    project_name: str
    description: str
    
    # Lineage
    template_source: Optional[str] = None  # sample ID this was forked from
    template_name: Optional[str] = None
    
    # State
    current_state: str = "scaffolded"  # scaffolded | compiles | runs | refined
    
    # Features
    features: FeatureSet = field(default_factory=FeatureSet)
    
    # Code inventory
    files: list[FileInfo] = field(default_factory=list)
    
    # Global patterns detected
    patterns: list[str] = field(default_factory=list)  # e.g., "state_machine", "sprite_animation"
    
    # Issues
    known_issues: list[KnownIssue] = field(default_factory=list)
    
    # Build info
    last_build_success: bool = False
    last_build_error: Optional[str] = None
    rom_size_bytes: int = 0
    
    # Timestamps
    created_at: str = ""
    last_updated: str = ""
    summary_generated_at: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectSummary':
        """Create from dictionary."""
        # Handle nested dataclasses
        if 'features' in data and isinstance(data['features'], dict):
            data['features'] = FeatureSet(**data['features'])
        
        if 'files' in data:
            files = []
            for f in data['files']:
                if isinstance(f, dict):
                    # Convert nested structs/functions
                    if 'structs' in f:
                        f['structs'] = [StructInfo(**s) if isinstance(s, dict) else s for s in f['structs']]
                    if 'functions' in f:
                        f['functions'] = [FunctionInfo(**fn) if isinstance(fn, dict) else fn for fn in f['functions']]
                    if 'constants' in f:
                        f['constants'] = [ConstantInfo(**c) if isinstance(c, dict) else c for c in f['constants']]
                    files.append(FileInfo(**f))
                else:
                    files.append(f)
            data['files'] = files
        
        if 'known_issues' in data:
            data['known_issues'] = [
                KnownIssue(**i) if isinstance(i, dict) else i 
                for i in data['known_issues']
            ]
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProjectSummary':
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


# Example summary structure (for documentation)
EXAMPLE_SUMMARY = {
    "project_id": "ed2ef6eb-d678-4d98-b43b-4c7b86c4d0dd",
    "project_name": "quad-pong",
    "description": "Pong variant with four AI paddles",
    "template_source": "pong",
    "template_name": "pong",
    "current_state": "compiles",
    "features": {
        "from_template": ["ball_physics", "paddle_collision", "scoring"],
        "added": ["four_paddles", "horizontal_ai", "multi_sprite_paddle"],
        "planned": []
    },
    "files": [
        {
            "path": "src/game.h",
            "description": "Core game definitions and state",
            "structs": [
                {
                    "name": "GameState",
                    "fields": [
                        {"name": "ball_x", "type": "uint8_t", "comment": "Ball X position"},
                        {"name": "ball_y", "type": "uint8_t", "comment": "Ball Y position"}
                    ],
                    "description": "Main game state container"
                }
            ],
            "functions": [],
            "constants": [
                {"name": "SCREEN_WIDTH", "value": "160", "comment": ""},
                {"name": "SPRITE_BALL", "value": "0", "comment": "Ball sprite index"}
            ],
            "includes": ["gb/gb.h", "stdint.h"],
            "lines": 243
        }
    ],
    "patterns": ["state_machine", "multi_sprite_entity", "ai_paddle"],
    "known_issues": [
        {
            "description": "White screen with numbers on start",
            "severity": "critical",
            "source": "human_feedback",
            "timestamp": "2026-01-21T13:48:28",
            "resolved": False
        }
    ],
    "last_build_success": True,
    "last_build_error": None,
    "rom_size_bytes": 32768,
    "created_at": "2026-01-21T13:27:30",
    "last_updated": "2026-01-21T13:51:46",
    "summary_generated_at": "2026-01-22T10:00:00"
}
