#!/usr/bin/env python3
"""
LLM-Powered Planning Agent using Claude Opus for high-level reasoning.

This agent uses the corpus as context and Claude to reason about:
- What features are needed for the game
- How to break down implementation into steps
- Which code references are most relevant
- Dependencies and ordering
"""

import json
import os
from datetime import datetime
from typing import Optional

import anthropic

from corpus_search import (
    load_manifest,
    get_feature_examples,
    read_sample_file,
    get_sample_files,
)
from plan_schema import ImplementationPlan, ImplementationStep, CodeReference


# System prompt for the planning agent
SYSTEM_PROMPT = """You are an expert GameBoy game developer and technical architect. Your role is to analyze game descriptions and create detailed implementation plans for GBDK-2020 (C-based GameBoy development).

You have access to a corpus of working, tested GameBoy game samples. Use these as references when creating plans.

## Your Responsibilities:
1. Analyze the game description to identify required features
2. Break down the implementation into logical, ordered steps
3. Identify which corpus samples are most relevant for each step
4. Specify dependencies between steps
5. Provide clear acceptance criteria

## GBDK-2020 Constraints:
- 8KB ROM bank size (can use banking for larger games)
- 8KB WRAM, 127 bytes HRAM
- 40 sprites max (8x8 or 8x16 pixels)
- 4 shades of gray only
- No floating point - use fixed-point or integers
- Use int8_t/uint8_t for most variables to save RAM
- vsync() for 60fps timing

## Output Format:
Return a JSON object with this structure:
{
  "game_type": "platformer|puzzle|action|rhythm|etc",
  "features": ["feature1", "feature2", ...],
  "feature_reasoning": "Why these features are needed...",
  "steps": [
    {
      "order": 1,
      "title": "Step Title",
      "description": "What to implement",
      "feature": "primary_feature",
      "complexity": 1-5,
      "dependencies": [],
      "acceptance_criteria": ["criterion1", "criterion2"],
      "recommended_samples": ["sample_id1", "sample_id2"],
      "implementation_notes": "Specific guidance..."
    }
  ],
  "notes": ["Important consideration 1", "Important consideration 2"],
  "estimated_hours": 2-20
}

Be thorough but practical. Each step should be completable in one coding session."""


class LLMPlanner:
    """Planning agent powered by Claude Opus."""
    
    def __init__(self, model: str = "claude-sonnet-4-20250514", verbose: bool = False):
        """
        Initialize the LLM planner.
        
        Args:
            model: Claude model to use (default: claude-sonnet-4-20250514 for cost efficiency,
                   use claude-opus-4-20250514 for maximum reasoning)
            verbose: Print debug information
        """
        self.client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
        self.model = model
        self.verbose = verbose
        self.manifest = load_manifest()
        
    def _build_corpus_context(self) -> str:
        """Build context string describing available corpus samples."""
        context_parts = ["## Available Corpus Samples\n"]
        
        # Add each sample with its features
        for sample in self.manifest.get("samples", []):
            sample_id = sample["id"]
            features = sample.get("teaches", [])
            desc = sample.get("description", "")
            
            context_parts.append(f"### {sample_id}")
            context_parts.append(f"**Description:** {desc}")
            context_parts.append(f"**Features:** {', '.join(features)}")
            context_parts.append("")
        
        # Add feature index for quick reference
        context_parts.append("## Feature Index")
        context_parts.append("Features and which samples demonstrate them:\n")
        
        feature_index = self.manifest.get("feature_index", {})
        for feature, samples in sorted(feature_index.items()):
            context_parts.append(f"- **{feature}**: {', '.join(samples)}")
        
        return "\n".join(context_parts)
    
    def _get_code_examples(self, features: list[str]) -> str:
        """Get relevant code examples for the identified features."""
        examples = []
        
        for feature in features[:5]:  # Limit to top 5 features
            feature_examples = get_feature_examples(feature)
            if feature_examples:
                examples.append(f"## Code Examples: {feature}\n")
                for ex in feature_examples[:2]:  # 2 examples per feature
                    examples.append(f"### From {ex['sample_id']}/{ex['file']}")
                    examples.append(f"```c\n{ex['code'][:1500]}\n```\n")  # Truncate long code
        
        return "\n".join(examples)
    
    def create_plan(self, game_description: str) -> ImplementationPlan:
        """
        Create an implementation plan using Claude.
        
        Args:
            game_description: Natural language description of the game
            
        Returns:
            ImplementationPlan with steps and references
        """
        if self.verbose:
            print(f"[LLM Planner] Using model: {self.model}")
            print(f"[LLM Planner] Analyzing: {game_description[:60]}...")
        
        # Build the user message with corpus context
        corpus_context = self._build_corpus_context()
        
        user_message = f"""## Game Description
{game_description}

## Corpus Context
{corpus_context}

Please analyze this game description and create a detailed implementation plan. Consider:
1. What features are essential vs nice-to-have?
2. What's the optimal order to implement features?
3. Which corpus samples should be referenced for each step?
4. What are potential gotchas or GameBoy-specific concerns?

Return your plan as a JSON object following the specified format."""

        if self.verbose:
            print(f"[LLM Planner] Sending request to Claude...")
        
        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        # Extract JSON from response
        response_text = response.content[0].text
        
        if self.verbose:
            print(f"[LLM Planner] Received response ({len(response_text)} chars)")
        
        # Parse the JSON (handle markdown code blocks)
        json_str = response_text
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        
        try:
            plan_data = json.loads(json_str.strip())
        except json.JSONDecodeError as e:
            if self.verbose:
                print(f"[LLM Planner] JSON parse error: {e}")
                print(f"[LLM Planner] Raw response:\n{response_text}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        
        # Convert to our schema
        return self._convert_to_plan(game_description, plan_data)
    
    def _convert_to_plan(self, description: str, data: dict) -> ImplementationPlan:
        """Convert LLM JSON response to ImplementationPlan."""
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        steps = []
        for step_data in data.get("steps", []):
            # Get code references for recommended samples
            references = []
            for sample_id in step_data.get("recommended_samples", [])[:3]:
                # Try to find relevant code from the sample
                feature = step_data.get("feature", "")
                ref = self._find_reference(sample_id, feature)
                if ref:
                    references.append(ref)
            
            step = ImplementationStep(
                order=step_data.get("order", len(steps) + 1),
                title=step_data.get("title", "Untitled Step"),
                description=step_data.get("description", ""),
                feature=step_data.get("feature", ""),
                estimated_complexity=step_data.get("complexity", 2),
                references=references,
                dependencies=step_data.get("dependencies", []),
                acceptance_criteria=step_data.get("acceptance_criteria", []),
            )
            steps.append(step)
        
        # Build notes including LLM's reasoning
        notes = data.get("notes", [])
        if data.get("feature_reasoning"):
            notes.insert(0, f"Feature rationale: {data['feature_reasoning']}")
        if data.get("estimated_hours"):
            notes.append(f"Estimated development time: {data['estimated_hours']} hours")
        
        return ImplementationPlan(
            id=plan_id,
            game_description=description,
            detected_game_type=data.get("game_type", "unknown"),
            required_features=data.get("features", []),
            feature_confidence={f: 1.0 for f in data.get("features", [])},  # LLM is confident
            relevant_samples=list(set(
                sample 
                for step in data.get("steps", [])
                for sample in step.get("recommended_samples", [])
            )),
            steps=steps,
            notes=notes,
        )
    
    def _find_reference(self, sample_id: str, feature: str) -> Optional[CodeReference]:
        """Find a code reference from a sample for a feature."""
        try:
            # Get the main game.c file
            files = get_sample_files(sample_id)
            game_file = next((f for f in files if f.endswith("game.c")), None)
            
            if not game_file:
                return None
            
            content = read_sample_file(sample_id, game_file)
            if not content:
                return None
            
            # Find a relevant function (simple heuristic)
            # Look for game_update, game_init, or feature-related functions
            func_names = ["game_update", "game_init", "game_render"]
            
            for func_name in func_names:
                if f"{func_name}(" in content or f"{func_name} (" in content:
                    # Extract the function
                    from corpus_search import extract_function
                    code = extract_function(content, func_name)
                    if code:
                        return CodeReference(
                            sample_id=sample_id,
                            file_path=game_file,
                            function_name=func_name,
                            description=f"Reference implementation from {sample_id}",
                            code_snippet=code[:1000],  # Truncate
                        )
            
            return None
        except Exception:
            return None


def main():
    """CLI for the LLM-powered planner."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create a GameBoy game implementation plan using Claude"
    )
    parser.add_argument(
        "description",
        help="Natural language description of the game to plan"
    )
    parser.add_argument(
        "-m", "--model",
        default="claude-sonnet-4-20250514",
        choices=["claude-sonnet-4-20250514", "claude-opus-4-20250514"],
        help="Claude model to use (default: sonnet for cost efficiency)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print debug information"
    )
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Get your API key from: https://console.anthropic.com/")
        return 1
    
    try:
        planner = LLMPlanner(model=args.model, verbose=args.verbose)
        plan = planner.create_plan(args.description)
        
        if args.format == "json":
            output = json.dumps(plan.to_dict(), indent=2)
        else:
            output = plan.to_markdown()
        
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Plan saved to {args.output}")
        else:
            print(output)
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
