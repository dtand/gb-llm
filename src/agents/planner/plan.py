"""
Planning Agent - Main entry point.

Analyzes game descriptions and produces structured implementation plans
by combining feature extraction with corpus search.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

from feature_extractor import extract_features, get_feature_summary
from corpus_search import (
    search_by_features,
    get_feature_examples,
    get_sample_files,
    read_sample_file,
    load_manifest
)
from plan_schema import (
    ImplementationPlan,
    ImplementationStep,
    CodeReference,
    generate_plan_id,
    create_step_from_template,
    STEP_TEMPLATES
)


class PlanningAgent:
    """
    High-reasoning planning agent that creates implementation plans.
    
    Takes a natural language game description and produces a structured
    plan with ordered steps and code references from the corpus.
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.manifest = load_manifest()
    
    def log(self, message: str):
        """Print message if verbose mode enabled."""
        if self.verbose:
            print(f"[Planner] {message}")
    
    def analyze(self, description: str) -> Dict:
        """
        Analyze a game description to extract requirements.
        
        Returns dict with features, game type, and relevant samples.
        """
        self.log(f"Analyzing: {description[:50]}...")
        
        # Extract features from description
        extraction = extract_features(description)
        self.log(f"Extracted {len(extraction['features'])} features")
        
        # Find relevant samples
        samples = search_by_features(extraction["features"])
        self.log(f"Found {len(samples)} relevant samples")
        
        return {
            "description": description,
            "extraction": extraction,
            "samples": samples
        }
    
    def create_plan(self, description: str) -> ImplementationPlan:
        """
        Create a complete implementation plan for a game.
        
        Args:
            description: Natural language game description
        
        Returns:
            ImplementationPlan with ordered steps and code references
        """
        analysis = self.analyze(description)
        extraction = analysis["extraction"]
        samples = analysis["samples"]
        
        # Determine which steps to include based on features
        steps = []
        step_order = 1
        
        # Always start with project setup
        setup_step = create_step_from_template("project_setup", step_order)
        setup_step.references = self._find_references("game_loop", samples)
        steps.append(setup_step)
        step_order += 1
        
        # Map features to step templates
        feature_to_template = {
            "sprites": "sprites_basic",
            "dpad": "player_movement",
            "gravity": "gravity_physics",
            "collision_aabb": "collision_detection",
            "collision_tile": "collision_detection",
            "backgrounds": "background_tiles",
            "tiles": "background_tiles",
            "scrolling": "scrolling",
            "music": "sound_setup",
            "sfx": "sound_setup",
            "save_sram": "save_system",
            "game_state": "game_loop_polish",
            "highscores": "save_system",
        }
        
        # Track which templates we've already added
        added_templates = {"project_setup"}
        
        # Add steps for each required feature
        for feature in extraction["features"]:
            template_key = feature_to_template.get(feature)
            
            if template_key and template_key not in added_templates:
                step = create_step_from_template(template_key, step_order)
                step.references = self._find_references(feature, samples)
                
                # Set dependencies
                if template_key in ["gravity_physics", "collision_detection"]:
                    # These depend on sprites being set up
                    if "sprites_basic" in added_templates:
                        step.dependencies = [2]  # Sprites step
                
                if template_key == "scrolling":
                    # Scrolling depends on background tiles
                    if "background_tiles" in added_templates:
                        for s in steps:
                            if s.title == "Background Tiles":
                                step.dependencies = [s.order]
                
                steps.append(step)
                added_templates.add(template_key)
                step_order += 1
        
        # Calculate total complexity
        total_complexity = min(5, sum(s.estimated_complexity for s in steps) // len(steps) + 1)
        
        # Create the plan
        plan = ImplementationPlan(
            id=generate_plan_id(),
            created_at=__import__("datetime").datetime.now().isoformat(),
            game_description=description,
            detected_game_type=extraction.get("game_type"),
            required_features=extraction["features"],
            feature_confidence=extraction["confidence"],
            relevant_samples=[s["id"] for s in samples[:5]],  # Top 5 samples
            steps=steps,
            estimated_total_complexity=total_complexity,
            notes=self._generate_notes(extraction, samples)
        )
        
        return plan
    
    def _find_references(self, feature: str, samples: List[Dict]) -> List[CodeReference]:
        """Find code references for a feature from relevant samples."""
        references = []
        examples = get_feature_examples(feature)
        
        for ex in examples[:3]:  # Limit to 3 examples per feature
            ref = CodeReference(
                sample_id=ex["sample_id"],
                file_path=ex["file"],
                function_name=ex.get("function"),
                description=f"Example of {feature} implementation",
                code_snippet=ex.get("code", "")[:500]  # Truncate long snippets
            )
            references.append(ref)
        
        return references
    
    def _generate_notes(self, extraction: Dict, samples: List[Dict]) -> List[str]:
        """Generate helpful notes for the implementation."""
        notes = []
        
        # Note about game type
        if extraction.get("game_type"):
            notes.append(f"This appears to be a {extraction['game_type']}-style game")
        
        # Note about best reference
        if samples:
            best = samples[0]
            notes.append(f"Best reference sample: {best['id']} (matches {best['relevance_score']} features)")
        
        # Note about low-confidence features
        low_conf = [f for f in extraction["features"] 
                   if extraction["confidence"].get(f, 0) < 0.5]
        if low_conf:
            notes.append(f"Low-confidence features (verify needed): {', '.join(low_conf)}")
        
        # Note about missing corpus coverage
        manifest = load_manifest()
        missing = manifest.get("missing_coverage", [])
        needed_missing = [f for f in extraction["features"] if f in missing]
        if needed_missing:
            notes.append(f"Warning: No corpus examples for: {', '.join(needed_missing)}")
        
        return notes


def main():
    parser = argparse.ArgumentParser(
        description="GameBoy game implementation planner"
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Game description to plan"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "markdown", "both"],
        default="both",
        help="Output format (default: both)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (without extension)"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze features, don't create full plan"
    )
    
    args = parser.parse_args()
    
    # Interactive mode if no description provided
    if not args.description:
        print("GameBoy Implementation Planner")
        print("=" * 40)
        print("Enter your game description:")
        args.description = input("> ").strip()
        if not args.description:
            print("No description provided, exiting.")
            sys.exit(1)
    
    # Create planner
    planner = PlanningAgent(verbose=args.verbose)
    
    # Analyze only mode
    if args.analyze_only:
        analysis = planner.analyze(args.description)
        print("\n" + get_feature_summary(analysis["extraction"]))
        print("\nRelevant samples:")
        for s in analysis["samples"][:5]:
            print(f"  - {s['id']}: {s['matched_features']}")
        sys.exit(0)
    
    # Create full plan
    plan = planner.create_plan(args.description)
    
    # Output
    if args.output:
        base_path = Path(args.output)
        if args.format in ["json", "both"]:
            json_path = base_path.with_suffix(".json")
            with open(json_path, "w") as f:
                f.write(plan.to_json())
            print(f"JSON plan written to: {json_path}")
        
        if args.format in ["markdown", "both"]:
            md_path = base_path.with_suffix(".md")
            with open(md_path, "w") as f:
                f.write(plan.to_markdown())
            print(f"Markdown plan written to: {md_path}")
    else:
        # Print to stdout
        if args.format == "json":
            print(plan.to_json())
        elif args.format == "markdown":
            print(plan.to_markdown())
        else:
            print("\n" + "=" * 60)
            print("IMPLEMENTATION PLAN")
            print("=" * 60)
            print(plan.to_markdown())
            print("\n" + "=" * 60)
            print("JSON OUTPUT")
            print("=" * 60)
            print(plan.to_json())


if __name__ == "__main__":
    main()
