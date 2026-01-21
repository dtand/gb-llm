"""
Plan schema and generation for the planning agent.

Defines the structure of implementation plans and provides utilities
for generating plans from feature requirements.
"""

import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class CodeReference:
    """Reference to a specific piece of code in the corpus."""
    sample_id: str
    file_path: str
    function_name: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    description: str = ""
    code_snippet: Optional[str] = None


@dataclass
class ImplementationStep:
    """A single step in the implementation plan."""
    order: int
    title: str
    description: str
    feature: str
    estimated_complexity: int  # 1-5
    references: List[CodeReference] = field(default_factory=list)
    dependencies: List[int] = field(default_factory=list)  # Step orders this depends on
    acceptance_criteria: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["references"] = [asdict(r) for r in self.references]
        return d


@dataclass 
class ImplementationPlan:
    """Complete implementation plan for a game."""
    id: str
    created_at: str
    game_description: str
    detected_game_type: Optional[str]
    required_features: List[str]
    feature_confidence: Dict[str, float]
    relevant_samples: List[str]
    steps: List[ImplementationStep]
    estimated_total_complexity: int
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        return d
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
    
    def to_markdown(self) -> str:
        """Generate a human-readable markdown version of the plan."""
        lines = [
            f"# Implementation Plan: {self.id}",
            f"",
            f"**Created:** {self.created_at}",
            f"",
            f"## Game Description",
            f"",
            f"> {self.game_description}",
            f"",
        ]
        
        if self.detected_game_type:
            lines.append(f"**Detected Type:** {self.detected_game_type}")
            lines.append("")
        
        lines.extend([
            f"## Required Features",
            f"",
        ])
        
        for feature in self.required_features:
            conf = self.feature_confidence.get(feature, 0)
            lines.append(f"- `{feature}` ({conf:.0%} confidence)")
        
        lines.extend([
            f"",
            f"## Reference Samples",
            f"",
        ])
        
        for sample in self.relevant_samples:
            lines.append(f"- `{sample}`")
        
        lines.extend([
            f"",
            f"## Implementation Steps",
            f"",
            f"**Estimated Total Complexity:** {self.estimated_total_complexity}/5",
            f"",
        ])
        
        for step in self.steps:
            deps = f" (depends on: {step.dependencies})" if step.dependencies else ""
            lines.extend([
                f"### Step {step.order}: {step.title}",
                f"",
                f"**Feature:** `{step.feature}` | **Complexity:** {step.estimated_complexity}/5{deps}",
                f"",
                f"{step.description}",
                f"",
            ])
            
            if step.references:
                lines.append("**References:**")
                for ref in step.references:
                    func = f"::{ref.function_name}()" if ref.function_name else ""
                    lines.append(f"- `{ref.sample_id}/{ref.file_path}{func}` - {ref.description}")
                lines.append("")
            
            if step.acceptance_criteria:
                lines.append("**Acceptance Criteria:**")
                for criterion in step.acceptance_criteria:
                    lines.append(f"- [ ] {criterion}")
                lines.append("")
        
        if self.notes:
            lines.extend([
                f"## Notes",
                f"",
            ])
            for note in self.notes:
                lines.append(f"- {note}")
        
        return "\n".join(lines)


# Standard implementation step templates
STEP_TEMPLATES = {
    "project_setup": ImplementationStep(
        order=0,
        title="Project Setup",
        description="Create project structure with Makefile, main.c, game.c, game.h, sprites.c, sprites.h",
        feature="game_loop",
        estimated_complexity=1,
        acceptance_criteria=[
            "Project compiles with `make`",
            "ROM runs in emulator (blank screen OK)",
            "All standard files created following CODE_STANDARDS.md"
        ]
    ),
    "sprites_basic": ImplementationStep(
        order=0,
        title="Basic Sprite Setup",
        description="Define sprite tile data and initialize OAM for game objects",
        feature="sprites",
        estimated_complexity=2,
        acceptance_criteria=[
            "Sprite data defined in sprites.c",
            "sprites_init() loads data to VRAM",
            "At least one sprite visible on screen"
        ]
    ),
    "player_movement": ImplementationStep(
        order=0,
        title="Player Movement",
        description="Implement D-pad input handling and player position updates",
        feature="dpad",
        estimated_complexity=1,
        acceptance_criteria=[
            "Player responds to D-pad input",
            "Movement is smooth (~60fps)",
            "Player stays within screen bounds"
        ]
    ),
    "gravity_physics": ImplementationStep(
        order=0,
        title="Gravity Physics",
        description="Add gravity accumulation and jump mechanics",
        feature="gravity",
        estimated_complexity=2,
        acceptance_criteria=[
            "Player falls when not on ground",
            "Jump has proper arc (rise then fall)",
            "Terminal velocity prevents infinite acceleration"
        ]
    ),
    "collision_detection": ImplementationStep(
        order=0,
        title="Collision Detection",
        description="Implement AABB collision between game objects",
        feature="collision_aabb",
        estimated_complexity=2,
        acceptance_criteria=[
            "Collisions detected between relevant objects",
            "Collision response is correct (bounce/stop/damage)",
            "No objects pass through each other"
        ]
    ),
    "background_tiles": ImplementationStep(
        order=0,
        title="Background Tiles",
        description="Design and load background tile map",
        feature="backgrounds",
        estimated_complexity=2,
        acceptance_criteria=[
            "Background tiles defined and loaded",
            "Tile map displays correctly",
            "No garbage tiles visible"
        ]
    ),
    "scrolling": ImplementationStep(
        order=0,
        title="Scrolling",
        description="Implement hardware scrolling using SCX/SCY registers",
        feature="scrolling",
        estimated_complexity=2,
        acceptance_criteria=[
            "Background scrolls smoothly",
            "Tile wrapping works correctly at boundaries",
            "Scroll position synced with game logic"
        ]
    ),
    "sound_setup": ImplementationStep(
        order=0,
        title="Sound Setup",
        description="Initialize sound hardware and implement basic audio",
        feature="music",
        estimated_complexity=2,
        acceptance_criteria=[
            "Sound registers configured correctly",
            "At least one sound plays",
            "No audio glitches or noise"
        ]
    ),
    "save_system": ImplementationStep(
        order=0,
        title="Save System",
        description="Implement SRAM save/load with magic number validation",
        feature="save_sram",
        estimated_complexity=2,
        acceptance_criteria=[
            "ROM header specifies MBC with RAM+BATTERY",
            "Save data persists across sessions",
            "Invalid saves handled gracefully"
        ]
    ),
    "game_loop_polish": ImplementationStep(
        order=0,
        title="Game Loop Polish",
        description="Add game states, win/lose conditions, and restart logic",
        feature="game_state",
        estimated_complexity=2,
        acceptance_criteria=[
            "Game has clear start state",
            "Win/lose conditions trigger correctly",
            "Player can restart without ROM reset"
        ]
    ),
}


def generate_plan_id() -> str:
    """Generate a unique plan ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"plan_{timestamp}"


def create_step_from_template(template_key: str, order: int, **overrides) -> ImplementationStep:
    """Create a step from a template with customizations."""
    if template_key not in STEP_TEMPLATES:
        raise ValueError(f"Unknown template: {template_key}")
    
    template = STEP_TEMPLATES[template_key]
    
    return ImplementationStep(
        order=order,
        title=overrides.get("title", template.title),
        description=overrides.get("description", template.description),
        feature=overrides.get("feature", template.feature),
        estimated_complexity=overrides.get("estimated_complexity", template.estimated_complexity),
        references=overrides.get("references", []),
        dependencies=overrides.get("dependencies", []),
        acceptance_criteria=overrides.get("acceptance_criteria", template.acceptance_criteria.copy())
    )
