"""
Plan schema for the LLM planning agent.

Defines the data structures for implementation plans.
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
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    game_description: str = ""
    detected_game_type: Optional[str] = None
    required_features: List[str] = field(default_factory=list)
    feature_confidence: Dict[str, float] = field(default_factory=dict)
    relevant_samples: List[str] = field(default_factory=list)
    steps: List[ImplementationStep] = field(default_factory=list)
    estimated_total_complexity: int = 0
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
            conf = self.feature_confidence.get(feature, 1.0)
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


def generate_plan_id() -> str:
    """Generate a unique plan ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"plan_{timestamp}"
