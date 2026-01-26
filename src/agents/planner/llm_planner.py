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
from pathlib import Path
from typing import Optional

# Load .env from project root
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

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
3. For each step, specify HARD REQUIREMENTS that MUST be followed
4. Identify which corpus samples are most relevant for each step
5. Specify dependencies between steps
6. Provide clear acceptance criteria
7. Generate a project name and README content

## GBDK-2020 Hard Constraints (MUST follow):
- 8KB ROM bank size (can use banking for larger games)
- 8KB WRAM, 127 bytes HRAM
- 40 sprites max (8x8 or 8x16 pixels)
- 4 shades of gray only (values 0-3)
- No floating point - use fixed-point or integers only
- Use int8_t/uint8_t for most variables to save RAM
- Use int16_t for positions that may exceed 127
- vsync() for 60fps timing
- Sprites need +8 offset for X, +16 for Y (hardware quirk)
- VRAM writes only during VBlank or with LCD off
- No malloc/dynamic allocation - static arrays only

## Output Format:
Return a JSON object with this structure:
{
  "project_name": "short-kebab-case-name",
  "readme_content": "# Game Title\\n\\nDescription of the game...\\n\\n## How to Play\\n\\n- D-Pad: Move\\n- A: Action\\n\\n## Features\\n\\n- Feature 1\\n- Feature 2",
  "game_type": "platformer|puzzle|action|rhythm|etc",
  "features": ["feature1", "feature2", ...],
  "feature_reasoning": "Why these features are needed...",
  "steps": [
    {
      "order": 1,
      "title": "Step Title",
      "description": "What to implement in detail",
      "feature": "primary_feature",
      "complexity": 1-5,
      "dependencies": [],
      "hard_requirements": [
        "MUST use int16_t for ball position to avoid overflow",
        "MUST check bounds before array access",
        "MUST NOT exceed 40 sprites total"
      ],
      "acceptance_criteria": ["criterion1", "criterion2"],
      "recommended_samples": ["sample_id1", "sample_id2"],
      "implementation_notes": "Specific guidance, gotchas, tips..."
    }
  ],
  "global_requirements": [
    "All game state in a single struct for clarity",
    "Use #define for magic numbers",
    "Keep main loop simple: input -> update -> render -> vsync"
  ],
  "notes": ["Important consideration 1", "Important consideration 2"],
  "estimated_hours": 2-20
}

## Project Naming Guidelines:
- Use kebab-case (lowercase with hyphens)
- Keep it short (2-4 words max)
- Make it descriptive of the game type
- Examples: "space-shooter", "puzzle-blocks", "endless-runner"

## README Guidelines:
- Start with a clear title and description
- Include "How to Play" with controls
- List main features
- Keep it concise but informative

## Hard Requirements Guidelines:
- MUST/MUST NOT indicate absolute requirements
- Focus on things that would cause bugs if violated
- Include type requirements (int8_t vs int16_t)
- Include bounds checking requirements
- Include hardware limitations (sprite count, VRAM timing)
- Include memory constraints

Be thorough but practical. Each step should be completable in one coding session."""


# System prompt for refinement mode
REFINEMENT_SYSTEM_PROMPT = """You are an expert GameBoy game developer debugging and fixing an existing game based on user feedback.

The user has played a generated GameBoy game and provided feedback about issues they encountered. Your job is to create a targeted fix plan.

## Context You'll Receive:
1. The original game description
2. The original implementation plan
3. The current source code files
4. User feedback describing the issues

## Your Responsibilities:
1. Analyze the user feedback to understand what's wrong
2. Review the current code to identify the root cause
3. Create a MINIMAL set of steps to fix the issues
4. Preserve what's working - don't rewrite unnecessarily
5. Focus on the specific problems mentioned

## GBDK-2020 Constraints (same as before):
- 8KB ROM bank size (can use banking for larger games)
- 8KB WRAM, 127 bytes HRAM
- 40 sprites max (8x8 or 8x16 pixels)
- 4 shades of gray only (values 0-3)
- No floating point - use fixed-point or integers only
- Use int8_t/uint8_t for most variables to save RAM
- Use int16_t for positions that may exceed 127
- vsync() for 60fps timing
- Sprites need +8 offset for X, +16 for Y (hardware quirk)
- VRAM writes only during VBlank or with LCD off
- No malloc/dynamic allocation - static arrays only

## Output Format:
Return a JSON object with this structure:
{
  "project_name": "same-as-original",
  "readme_content": "Keep existing or update if features changed",
  "game_type": "same-as-original",
  "features": ["same features"],
  "feature_reasoning": "Analysis of the feedback and what needs fixing",
  "steps": [
    {
      "order": 1,
      "title": "Fix: Issue Title",
      "description": "Detailed description of what to fix and how",
      "feature": "relevant_feature",
      "complexity": 1-3,
      "dependencies": [],
      "hard_requirements": [
        "MUST preserve existing working functionality",
        "MUST only modify files related to this fix"
      ],
      "acceptance_criteria": ["User feedback issue is resolved"],
      "recommended_samples": [],
      "implementation_notes": "Specific code changes needed..."
    }
  ],
  "global_requirements": [
    "Preserve all existing functionality not mentioned in feedback",
    "Minimize code changes to reduce risk of new bugs"
  ],
  "notes": ["What was wrong", "How we're fixing it"],
  "estimated_hours": 1-4
}

## Important Guidelines:
- Create FEWER steps than the original plan (usually 1-3 fix steps)
- Each step should address a specific issue from the feedback
- Include the EXACT code changes needed when possible
- Don't refactor working code unless it's causing the bug
- Preserve the original game structure and naming"""


# Try to import vector search (optional dependency)
try:
    from src.corpus.vectordb import CorpusSearch
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False


class LLMPlanner:
    """Planning agent powered by Claude Opus."""
    
    def __init__(self, model: str = "claude-sonnet-4-20250514", verbose: bool = False, use_vector_search: bool = True):
        """
        Initialize the LLM planner.
        
        Args:
            model: Claude model to use (default: claude-sonnet-4-20250514 for cost efficiency,
                   use claude-opus-4-20250514 for maximum reasoning)
            verbose: Print debug information
            use_vector_search: Whether to use vector DB for semantic search (if available)
        """
        self.client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
        self.model = model
        self.verbose = verbose
        self.manifest = load_manifest()
        
        # Initialize vector search if available and requested
        self.corpus_search = None
        if use_vector_search and VECTOR_SEARCH_AVAILABLE:
            try:
                self.corpus_search = CorpusSearch()
                if self.verbose:
                    stats = self.corpus_search.get_stats()
                    print(f"[LLM Planner] Vector search enabled ({stats['total']} indexed chunks)")
            except Exception as e:
                if self.verbose:
                    print(f"[LLM Planner] Vector search unavailable: {e}")
    
    def _stream_message(self, system: str, prompt: str, max_tokens: int = 8192) -> dict:
        """
        Call Claude API with streaming to avoid timeout errors.
        
        Returns dict with 'text' (response content) and 'stop_reason'.
        """
        response_text = ""
        stop_reason = None
        
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                response_text += text
            final_message = stream.get_final_message()
            stop_reason = final_message.stop_reason
        
        return {"text": response_text, "stop_reason": stop_reason}
        
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
    
    def _get_semantic_context(self, description: str) -> str:
        """
        Get semantically relevant code examples using vector search.
        
        Args:
            description: Game or task description
            
        Returns:
            Formatted context string with relevant code examples
        """
        if not self.corpus_search:
            return ""
        
        try:
            context = self.corpus_search.get_context_for_task(description)
            if self.verbose:
                print(f"[LLM Planner] Vector search returned {len(context)} chars of context")
            return context
        except Exception as e:
            if self.verbose:
                print(f"[LLM Planner] Vector search error: {e}")
            return ""
    
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
        
        # Get semantic context from vector search if available
        semantic_context = self._get_semantic_context(game_description)
        
        user_message = f"""## Game Description
{game_description}

## Corpus Context
{corpus_context}"""

        # Add semantic context if available
        if semantic_context:
            user_message += f"""

## Semantically Relevant Code Examples
The following code examples were found to be semantically similar to your game description:

{semantic_context}"""

        user_message += """

Please analyze this game description and create a detailed implementation plan. Consider:
1. What features are essential vs nice-to-have?
2. What's the optimal order to implement features?
3. Which corpus samples should be referenced for each step?
4. What are potential gotchas or GameBoy-specific concerns?

Return your plan as a JSON object following the specified format."""

        if self.verbose:
            print(f"[LLM Planner] Sending request to Claude...")
        
        # Call Claude with streaming (avoids timeout errors)
        response = self._stream_message(SYSTEM_PROMPT, user_message, max_tokens=4096)
        
        # Extract JSON from response
        response_text = response["text"]
        
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
    
    def create_refinement_plan(
        self,
        original_description: str,
        original_plan: dict,
        current_code: dict[str, str],
        user_feedback: str,
    ) -> ImplementationPlan:
        """
        Create a refinement plan based on user feedback.
        
        Args:
            original_description: The original game description
            original_plan: The original implementation plan (as dict)
            current_code: Dict mapping file paths to their contents
            user_feedback: User's feedback about what needs fixing
            
        Returns:
            ImplementationPlan with fix steps
        """
        if self.verbose:
            print(f"[LLM Planner] Creating refinement plan...")
            print(f"[LLM Planner] Feedback: {user_feedback[:100]}...")
        
        # Build context with current code
        code_context = "\n\n".join([
            f"### {path}\n```c\n{code}\n```"
            for path, code in current_code.items()
        ])
        
        # Summarize original plan
        original_steps = original_plan.get("steps", [])
        plan_summary = "\n".join([
            f"- Step {s.get('order', i+1)}: {s.get('title', 'Untitled')}"
            for i, s in enumerate(original_steps)
        ])
        
        # Get semantic context for the feedback (helps with sprite/visual issues)
        semantic_context = self._get_semantic_context(user_feedback)
        
        user_message = f"""## Original Game Description
{original_description}

## Original Implementation Plan
Project: {original_plan.get('project_name', 'unknown')}
Game Type: {original_plan.get('detected_game_type', 'unknown')}
Features: {', '.join(original_plan.get('required_features', []))}

Steps:
{plan_summary}

## Current Source Code
{code_context}

## User Feedback
{user_feedback}"""

        # Add semantic context if available (especially useful for sprite/visual fixes)
        if semantic_context:
            user_message += f"""

## Reference Examples
The following code examples may be relevant to the requested changes:

{semantic_context}"""

        user_message += """

Please analyze the feedback and create a targeted fix plan. Focus on:
1. What specific issues does the feedback describe?
2. Which files/functions need to be modified?
3. What's the minimal change to fix each issue?
4. How can we avoid breaking existing functionality?

Return a fix plan as a JSON object following the specified format."""

        if self.verbose:
            print(f"[LLM Planner] Sending refinement request to Claude...")
        
        # Call Claude with streaming (avoids timeout errors)
        response = self._stream_message(REFINEMENT_SYSTEM_PROMPT, user_message, max_tokens=8192)
        
        response_text = response["text"]
        
        if self.verbose:
            print(f"[LLM Planner] Received refinement response ({len(response_text)} chars)")
        
        # Parse JSON
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
                print(f"[LLM Planner] Attempting JSON repair...")
            
            # Try to repair truncated/malformed JSON
            plan_data = self._repair_json(json_str.strip(), original_plan)
            
            if plan_data is None:
                if self.verbose:
                    print(f"[LLM Planner] Raw response:\n{response_text}")
                raise ValueError(f"Failed to parse refinement plan as JSON: {e}")
        
        # Use original project name if not provided
        if not plan_data.get("project_name"):
            plan_data["project_name"] = original_plan.get("project_name", "game")
        
        return self._convert_to_plan(original_description, plan_data)
    
    def _repair_json(self, json_str: str, original_plan: dict) -> Optional[dict]:
        """Attempt to repair truncated or malformed JSON."""
        import re
        
        # Try adding closing brackets/braces
        attempts = [
            json_str,
            json_str + '}',
            json_str + '"}',
            json_str + '"]',
            json_str + '"]}',
            json_str + '"}]}',
            json_str + '"]}]}',
            json_str + '"}],"notes":[],"project_name":"' + original_plan.get("project_name", "game") + '"}',
        ]
        
        for attempt in attempts:
            # Try to balance brackets
            open_braces = attempt.count('{') - attempt.count('}')
            open_brackets = attempt.count('[') - attempt.count(']')
            
            fixed = attempt
            fixed += ']' * max(0, open_brackets)
            fixed += '}' * max(0, open_braces)
            
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                continue
        
        # Try to extract at least the steps array
        steps_match = re.search(r'"steps"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
        if steps_match:
            try:
                # Try to parse just the steps and build a minimal plan
                steps_json = '[' + steps_match.group(1) + ']'
                # Fix common issues
                steps_json = re.sub(r',\s*]', ']', steps_json)  # Remove trailing commas
                steps = json.loads(steps_json)
                
                return {
                    "project_name": original_plan.get("project_name", "game"),
                    "game_type": original_plan.get("detected_game_type", "unknown"),
                    "features": original_plan.get("required_features", []),
                    "steps": steps,
                    "notes": ["Plan recovered from partial JSON response"],
                }
            except json.JSONDecodeError:
                pass
        
        return None
    
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
                hard_requirements=step_data.get("hard_requirements", []),
                acceptance_criteria=step_data.get("acceptance_criteria", []),
                implementation_notes=step_data.get("implementation_notes", ""),
            )
            steps.append(step)
        
        # Build notes including LLM's reasoning
        notes = data.get("notes", [])
        if data.get("feature_reasoning"):
            notes.insert(0, f"Feature rationale: {data['feature_reasoning']}")
        if data.get("estimated_hours"):
            notes.append(f"Estimated development time: {data['estimated_hours']} hours")
        
        plan = ImplementationPlan(
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
            global_requirements=data.get("global_requirements", []),
            notes=notes,
            project_name=data.get("project_name", "untitled-game"),
            readme_content=data.get("readme_content", f"# {data.get('project_name', 'Game')}\n\n{description}"),
        )
        
        # Enrich each step with relevant code from vector search
        self._enrich_plan_with_vector_search(plan)
        
        return plan
    
    def _enrich_plan_with_vector_search(self, plan: ImplementationPlan) -> None:
        """
        Enrich each step in the plan with relevant code from vector search.
        
        This adds actual code examples to each step's context_code field,
        so the coder has concrete examples to reference.
        """
        if not self.corpus_search:
            return
        
        for step in plan.steps:
            # Build a search query from the step's info
            search_query = f"{step.title} {step.description} {step.feature}"
            
            try:
                # Search for relevant functions
                func_results = self.corpus_search.search_functions(search_query, n_results=2)
                
                # Search for sprites if the step seems sprite-related
                sprite_keywords = ['sprite', 'player', 'enemy', 'character', 'animation', 'tile', 'visual']
                if any(kw in search_query.lower() for kw in sprite_keywords):
                    sprite_results = self.corpus_search.search_sprites(search_query, n_results=2)
                else:
                    sprite_results = []
                
                # Build context_code list
                context_code = []
                
                for result in func_results:
                    context_code.append({
                        'type': 'function',
                        'name': result.name,
                        'sample_id': result.sample_id,
                        'file': result.file,
                        'code': result.code,
                        'description': result.description,
                        'relevance': result.relevance,
                    })
                
                for result in sprite_results:
                    context_code.append({
                        'type': 'sprite',
                        'name': result.name,
                        'sample_id': result.sample_id,
                        'file': result.file,
                        'code': result.code,
                        'description': result.description,
                        'relevance': result.relevance,
                        'ascii_preview': result.metadata.get('ascii_preview', ''),
                    })
                
                step.context_code = context_code
                
                if self.verbose and context_code:
                    print(f"[LLM Planner] Step {step.order}: Added {len(context_code)} code examples from vector search")
                    
            except Exception as e:
                if self.verbose:
                    print(f"[LLM Planner] Vector search error for step {step.order}: {e}")
    
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
