"""
Designer Agent - Summary-first context orchestration.

The Designer agent is responsible for:
1. Loading project summary (JSON) → understand current state
2. Parsing user request → identify required features
3. Gap analysis → what's missing vs what's already built
4. Selective corpus query (Vector DB) → only for net-new patterns
5. Assembling minimal context package for Coder
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

import anthropic

# Imports
from ..context.schemas import ProjectSummary, FeatureSet
from ..context.summary_generator import generate_summary
from ..project_api import get_api, ProjectAPI

# Try to import vector search
try:
    from src.corpus.vectordb import CorpusSearch
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SAMPLES_DIR = PROJECT_ROOT / "games" / "samples"


@dataclass
class FeatureGap:
    """A feature that needs to be implemented."""
    name: str
    description: str
    complexity: int  # 1-5
    corpus_queries: list[str]  # Queries to find relevant patterns
    depends_on: list[str] = field(default_factory=list)


@dataclass
class Modification:
    """A modification to an existing feature."""
    feature: str  # Name of existing feature to modify
    change: str   # Description of what to change/fix
    files: list[str] = field(default_factory=list)  # Files likely to be modified


@dataclass
class SchemaChange:
    """Changes to the data schema for content-driven features."""
    add_tables: list[dict] = field(default_factory=list)  # New tables to add
    add_fields: list[dict] = field(default_factory=list)  # Fields to add to existing tables
    remove_tables: list[str] = field(default_factory=list)
    remove_fields: list[dict] = field(default_factory=list)


@dataclass
class ImplementationStep:
    """A single step in the implementation plan - small enough for one LLM call."""
    order: int
    title: str
    description: str
    feature: str  # Which feature_gap this implements (or "modification" for mods)
    files_to_modify: list[str] = field(default_factory=list)
    hard_requirements: list[str] = field(default_factory=list)  # MUST/MUST NOT rules
    acceptance_criteria: list[str] = field(default_factory=list)
    corpus_hints: list[str] = field(default_factory=list)  # Queries for relevant examples


@dataclass
class ContextPackage:
    """
    Assembled context for the Coder agent.
    
    Contains only what's needed for the current task - no extraneous context.
    """
    # Project state
    project_id: str
    project_name: str
    current_state: str  # scaffolded, compiles, runs, refined
    
    # What exists
    existing_files: list[dict]  # [{path, description, key_functions}]
    existing_features: list[str]
    existing_patterns: list[str]
    
    # What's needed
    user_request: str
    feature_gaps: list[FeatureGap]
    modifications: list[Modification] = field(default_factory=list)  # Changes to existing features
    schema_changes: Optional[SchemaChange] = None  # Data schema changes
    
    # Implementation steps (ordered, one at a time for coder)
    implementation_steps: list[ImplementationStep] = field(default_factory=list)
    
    # Relevant examples from corpus
    corpus_examples: list[dict] = field(default_factory=list)  # [{source, code, relevance}]
    
    # Known issues to avoid
    known_issues: list[str] = field(default_factory=list)
    
    # Constraints
    constraints: list[str] = field(default_factory=list)
    
    def to_prompt_context(self) -> str:
        """Convert to a formatted string for LLM prompt."""
        sections = []
        
        # Project state
        sections.append(f"## Project: {self.project_name}")
        sections.append(f"Current state: {self.current_state}")
        sections.append("")
        
        # Existing files
        sections.append("## Existing Files")
        for f in self.existing_files:
            funcs = ", ".join(f.get("key_functions", [])[:5])
            sections.append(f"- **{f['path']}**: {f.get('description', '')} [{funcs}]")
        sections.append("")
        
        # Existing features
        if self.existing_features:
            sections.append("## Already Implemented Features")
            sections.append(", ".join(self.existing_features))
            sections.append("")
        
        # User request
        sections.append("## User Request")
        sections.append(self.user_request)
        sections.append("")
        
        # Feature gaps
        if self.feature_gaps:
            sections.append("## Features to Implement")
            for gap in self.feature_gaps:
                deps = f" (depends on: {', '.join(gap.depends_on)})" if gap.depends_on else ""
                sections.append(f"- **{gap.name}** (complexity {gap.complexity}): {gap.description}{deps}")
            sections.append("")
        
        # Modifications to existing features
        if self.modifications:
            sections.append("## Modifications to Existing Features")
            for mod in self.modifications:
                files = f" (files: {', '.join(mod.files)})" if mod.files else ""
                sections.append(f"- **{mod.feature}**: {mod.change}{files}")
            sections.append("")
        
        # Schema changes
        if self.schema_changes:
            sections.append("## Data Schema Changes")
            if self.schema_changes.add_tables:
                sections.append("### New Tables")
                for table in self.schema_changes.add_tables:
                    sections.append(f"- **{table['name']}**: {table.get('description', '')}")
                    for field_name, field_def in table.get('fields', {}).items():
                        sections.append(f"  - {field_name}: {field_def['type']}")
            if self.schema_changes.add_fields:
                sections.append("### New Fields")
                for field_add in self.schema_changes.add_fields:
                    sections.append(f"- {field_add['table']}.{field_add['name']}: {field_add['field']['type']}")
            sections.append("")
        
        # Corpus examples
        if self.corpus_examples:
            sections.append("## Reference Code Examples")
            for ex in self.corpus_examples:
                sections.append(f"### From {ex['source']} (relevance: {ex.get('relevance', 'high')})")
                sections.append(f"```c\n{ex['code']}\n```")
                sections.append("")
        
        # Known issues
        if self.known_issues:
            sections.append("## Known Issues to Avoid")
            for issue in self.known_issues:
                sections.append(f"- {issue}")
            sections.append("")
        
        # Constraints
        if self.constraints:
            sections.append("## Constraints")
            for c in self.constraints:
                sections.append(f"- {c}")
        
        return "\n".join(sections)
    
    def to_step_context(self, step: 'ImplementationStep', step_corpus_examples: list[dict] = None) -> str:
        """
        Convert to context for a SINGLE implementation step.
        
        This produces a focused prompt for one step at a time, avoiding context overload.
        
        Args:
            step: The specific ImplementationStep to generate context for
            step_corpus_examples: Corpus examples specific to this step (from step.corpus_hints)
        """
        sections = []
        
        # Project state (brief)
        sections.append(f"## Project: {self.project_name}")
        sections.append(f"Current state: {self.current_state}")
        sections.append("")
        
        # Overall goal (brief context)
        sections.append("## Overall Goal")
        sections.append(self.user_request)
        sections.append("")
        
        # Current step details (THE FOCUS)
        total_steps = len(self.implementation_steps)
        sections.append(f"## Current Step: {step.order}/{total_steps} - {step.title}")
        sections.append(f"**Description:** {step.description}")
        sections.append(f"**Feature:** {step.feature}")
        sections.append("")
        
        # Files to modify for this step
        if step.files_to_modify:
            sections.append("### Files to Modify")
            for f in step.files_to_modify:
                sections.append(f"- {f}")
            sections.append("")
        
        # Hard requirements for this step
        if step.hard_requirements:
            sections.append("### MUST Follow These Rules")
            for req in step.hard_requirements:
                sections.append(f"- {req}")
            sections.append("")
        
        # Acceptance criteria
        if step.acceptance_criteria:
            sections.append("### Acceptance Criteria")
            for criterion in step.acceptance_criteria:
                sections.append(f"- [ ] {criterion}")
            sections.append("")
        
        # Schema changes (if relevant to this step)
        if self.schema_changes and step.order == 1:  # Usually step 1 handles data structures
            sections.append("## Data Schema Changes")
            if self.schema_changes.add_tables:
                sections.append("### New Tables to Define")
                for table in self.schema_changes.add_tables:
                    sections.append(f"- **{table['name']}**: {table.get('description', '')}")
                    for field_name, field_def in table.get('fields', {}).items():
                        sections.append(f"  - {field_name}: {field_def['type']}")
            sections.append("")
        
        # Corpus examples for THIS step
        examples = step_corpus_examples or []
        if examples:
            sections.append("## Reference Code for This Step")
            for ex in examples[:3]:  # Limit to 3 examples per step
                sections.append(f"### From {ex['source']}")
                sections.append(f"```c\n{ex['code']}\n```")
                sections.append("")
        
        # Known issues
        if self.known_issues:
            sections.append("## Known Issues to Avoid")
            for issue in self.known_issues:
                sections.append(f"- {issue}")
            sections.append("")
        
        return "\n".join(sections)


# System prompt for the Designer agent
DESIGNER_SYSTEM_PROMPT = """You are a GameBoy game architect analyzing what code changes are needed for a specific user request.

You will receive:
1. A project summary showing current state, files, features, and patterns
2. A user request for a specific change or feature

Your job is to:
1. Identify ONLY what's needed to implement the user's EXACT request
2. Plan proper FILE ORGANIZATION - create new files for major systems
3. Break the work into small, sequential implementation steps

CRITICAL: FILE ORGANIZATION
Do NOT put all code in game.c! Create separate files for each major system:
- game.h/game.c - Core game state, main loop only
- enemies.h/enemies.c - Enemy system (spawning, movement, types)
- combat.h/combat.c - Battle system, damage calculations
- player.h/player.c - Player stats, inventory, leveling
- ui.h/ui.c - HUD, menus, text display
- items.h/items.c - Item system, loot, chests

Each .c file should be under 300 lines. If game.c is already large, move existing code to new files.

CRITICAL RULES:
- ONLY return items that are DIRECTLY REQUIRED to fulfill the user's specific request
- Do NOT suggest improvements, enhancements, or "nice to have" features
- Do NOT suggest features the user didn't explicitly ask for
- Create NEW FILES for new major systems instead of bloating game.c

THREE TYPES OF WORK:
1. **feature_gaps** - NEW features that don't exist yet
2. **modifications** - Changes/fixes to EXISTING features
3. **schema_changes** - Data table changes for content-driven features

IMPLEMENTATION STEPS - CRITICAL:
After identifying feature_gaps and modifications, break ALL work into small sequential steps.
Each step should be small enough to implement in ONE focused coding session (1-2 files, ~100-200 lines changed).

Step guidelines:
- Step 1: Create new header file with structs/constants/prototypes
- Step 2: Create new .c file with implementation
- Step 3: Integrate by adding #include and function calls to game.c
- Complex features should create their own file pair (foo.h/foo.c)
- Each step must result in compilable code

Example - "add enemy system":
  files_to_create: ["src/enemies.h", "src/enemies.c"]
  implementation_steps:
    Step 1: Create enemies.h with Enemy struct, types, and function prototypes
    Step 2: Create enemies.c with spawn, update, and render functions
    Step 3: Integrate enemies into game.c (include header, call functions)

Output a JSON object:
{
  "understanding": "Brief summary of what the user wants",
  "existing_capabilities": ["list of relevant features already in the code"],
  "feature_gaps": [
    {
      "name": "feature_name",
      "description": "What this NEW feature does",
      "complexity": 1-5,
      "corpus_queries": ["query1", "query2"],
      "depends_on": ["other_feature_name"]
    }
  ],
  "modifications": [
    {
      "feature": "existing_feature_name",
      "change": "What to fix or adjust",
      "files": ["src/game.c"]
    }
  ],
  "schema_changes": {
    "add_tables": [
      {
        "name": "table_name",
        "description": "What this table stores",
        "fields": {
          "id": {"type": "uint8", "auto": true},
          "name": {"type": "string", "length": 10, "required": true},
          "hp": {"type": "uint8", "min": 1, "max": 255, "default": 10}
        }
      }
    ],
    "add_fields": [
      {"table": "existing_table", "name": "new_field", "field": {"type": "uint8"}}
    ]
  },
  "implementation_steps": [
    {
      "order": 1,
      "title": "Short descriptive title",
      "description": "What this step accomplishes",
      "feature": "which feature_gap or 'modification' this implements",
      "files_to_modify": ["src/enemies.h"],
      "files_to_create": ["src/enemies.h"],
      "hard_requirements": ["MUST define X before Y", "MUST NOT use malloc"],
      "acceptance_criteria": ["Enemy struct exists", "Constants defined"],
      "corpus_hints": ["enemy struct", "sprite constants"]
    }
  ],
  "files_to_modify": ["src/game.c"],
  "files_to_create": ["src/enemies.h", "src/enemies.c"],
  "warnings": ["potential issue 1", "gotcha 2"]
}

SCHEMA FIELD TYPES:
- uint8, int8, uint16, int16: Integer types with optional min/max
- string: Fixed-length string with required "length" property
- bool: Boolean (stored as uint8)
- enum: Enumerated type with "values" array
- ref: Reference to another table with "target" and optional "nullable"

Keep feature_gaps/modifications MINIMAL, create NEW FILES for new systems, break work into small steps."""


class DesignerAgent:
    """
    Designer agent for summary-first context orchestration.
    
    The Designer reads the project summary to understand current state,
    analyzes user requests to identify feature gaps, and assembles
    minimal context for the Coder agent.
    """
    
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        verbose: bool = False,
        log_callback: callable = None
    ):
        """
        Initialize the Designer agent.
        
        Args:
            model: Claude model for gap analysis
            verbose: Print debug information
            log_callback: Optional callback(level, message) for log messages
        """
        self.client = anthropic.Anthropic()
        self.model = model
        self.verbose = verbose
        self.log_callback = log_callback
        self.api = get_api()
        
        # Initialize vector search if available
        self.corpus_search = None
        if VECTOR_SEARCH_AVAILABLE:
            try:
                self.corpus_search = CorpusSearch()
                if self.verbose:
                    print(f"[Designer] Vector search enabled")
            except Exception as e:
                if self.verbose:
                    print(f"[Designer] Vector search unavailable: {e}")
    
    def _log(self, level: str, message: str):
        """Log a message to console and callback."""
        if self.verbose:
            print(f"[Designer] {message}")
        if self.log_callback:
            try:
                self.log_callback(level, message)
            except Exception:
                pass
    
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
    
    def analyze_request(
        self,
        project_id: str,
        user_request: str
    ) -> dict:
        """
        Analyze a user request against current project state.
        
        Args:
            project_id: The project to analyze
            user_request: What the user wants to do
            
        Returns:
            Analysis dict with gaps, modifications, etc.
        """
        # Load project summary
        project = self.api.get_project(project_id)
        summary = project.summary
        
        if not summary:
            raise ValueError(f"Project {project_id} has no summary")
        
        self._log("info", f"📊 Project: {project.name}")
        self._log("info", f"   State: {summary.current_state}")
        self._log("info", f"   🤖 Calling Claude for gap analysis...")
        
        # Build prompt with summary context
        summary_context = self._format_summary_for_prompt(summary)
        
        user_message = f"""## Current Project State
{summary_context}

## User Request
{user_request}

Analyze what needs to change to fulfill this request. Focus on MINIMAL changes - extend existing code where possible."""

        # Call Claude for gap analysis with streaming (avoids timeout errors)
        response = self._stream_message(DESIGNER_SYSTEM_PROMPT, user_message)
        
        # Parse response
        response_text = response["text"]
        
        # Extract JSON
        try:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0]
            else:
                json_str = response_text
            
            analysis = json.loads(json_str)
        except json.JSONDecodeError as e:
            self._log("warning", f"   ⚠️ Failed to parse analysis JSON")
            analysis = {
                "understanding": user_request,
                "feature_gaps": [],
                "warnings": [f"Could not parse analysis: {e}"]
            }
        
        # Log what we found
        gaps = analysis.get('feature_gaps', [])
        mods = analysis.get('modifications', [])
        steps = analysis.get('implementation_steps', [])
        
        if gaps:
            self._log("info", f"   📋 Found {len(gaps)} feature gap(s)")
            for g in gaps[:3]:
                name = g.get('name', g) if isinstance(g, dict) else str(g)
                self._log("info", f"      • {name}")
        if mods:
            self._log("info", f"   🔧 Found {len(mods)} modification(s)")
        if steps:
            self._log("info", f"   📝 {len(steps)} implementation step(s) planned")
        
        return analysis
    
    def _format_summary_for_prompt(self, summary: ProjectSummary) -> str:
        """Format project summary for the LLM prompt."""
        sections = []
        
        sections.append(f"**Project:** {summary.project_name}")
        sections.append(f"**State:** {summary.current_state}")
        
        if summary.template_source:
            sections.append(f"**Based on:** {summary.template_source} template")
        
        # Features
        all_features = (
            summary.features.from_template + 
            summary.features.added
        )
        if all_features:
            sections.append(f"**Features:** {', '.join(all_features)}")
        
        # Patterns
        if summary.patterns:
            sections.append(f"**Patterns detected:** {', '.join(summary.patterns)}")
        
        # Files
        sections.append("\n**Files:**")
        for f in summary.files:
            funcs = [fn.name for fn in f.functions][:5]
            structs = [s.name for s in f.structs]
            
            details = []
            if funcs:
                details.append(f"functions: {', '.join(funcs)}")
            if structs:
                details.append(f"structs: {', '.join(structs)}")
            
            detail_str = f" ({'; '.join(details)})" if details else ""
            sections.append(f"- {f.path}: {f.description}{detail_str}")
        
        # Known issues
        if summary.known_issues:
            sections.append("\n**Known issues:**")
            for issue in summary.known_issues:
                sections.append(f"- [{issue.severity}] {issue.description}")
        
        return "\n".join(sections)
    
    def get_corpus_examples(
        self,
        queries: list[str],
        max_examples: int = 5
    ) -> list[dict]:
        """
        Query the corpus for relevant code examples.
        
        Args:
            queries: Search queries for different features
            max_examples: Maximum total examples to return
            
        Returns:
            List of {source, code, relevance} dicts
        """
        if not self.corpus_search:
            if self.verbose:
                print("[Designer] Vector search not available, skipping corpus query")
            return []
        
        examples = []
        seen_sources = set()
        
        for query in queries:
            if len(examples) >= max_examples:
                break
            
            try:
                # Use search_functions which is the main search method
                results = self.corpus_search.search_functions(query, n_results=3)
                
                for result in results:
                    source = f"{result.sample_id}/{result.file}"
                    
                    # Deduplicate
                    if source in seen_sources:
                        continue
                    seen_sources.add(source)
                    
                    examples.append({
                        "source": source,
                        "code": result.code[:1500] if result.code else "",  # Truncate
                        "relevance": "high" if result.relevance > 0.8 else "medium",
                        "query": query,
                        "name": result.name
                    })
                    
                    if len(examples) >= max_examples:
                        break
                        
            except Exception as e:
                if self.verbose:
                    print(f"[Designer] Corpus query failed: {e}")
        
        if self.verbose:
            print(f"[Designer] Found {len(examples)} corpus examples")
        
        return examples
    
    def assemble_context(
        self,
        project_id: str,
        user_request: str
    ) -> ContextPackage:
        """
        Assemble a minimal context package for the Coder agent.
        
        This is the main entry point - it:
        1. Loads project summary
        2. Analyzes the request for gaps
        3. Queries corpus for relevant examples
        4. Packages everything together
        
        Args:
            project_id: The project to work on
            user_request: What the user wants
            
        Returns:
            ContextPackage with everything the Coder needs
        """
        # Get project and summary
        project = self.api.get_project(project_id)
        summary = project.summary
        
        if not summary:
            raise ValueError(f"Project {project_id} has no summary")
        
        # Analyze request
        analysis = self.analyze_request(project_id, user_request)
        
        # Build feature gaps
        feature_gaps = []
        corpus_queries = []
        
        for gap_data in analysis.get("feature_gaps", []):
            gap = FeatureGap(
                name=gap_data.get("name", "unknown"),
                description=gap_data.get("description", ""),
                complexity=gap_data.get("complexity", 3),
                corpus_queries=gap_data.get("corpus_queries", []),
                depends_on=gap_data.get("depends_on", [])
            )
            feature_gaps.append(gap)
            corpus_queries.extend(gap.corpus_queries)
        
        # Build modifications to existing features
        modifications = []
        for mod_data in analysis.get("modifications", []):
            mod = Modification(
                feature=mod_data.get("feature", "unknown"),
                change=mod_data.get("change", ""),
                files=mod_data.get("files", [])
            )
            modifications.append(mod)
        
        # Build schema changes
        schema_changes = None
        schema_data = analysis.get("schema_changes")
        if schema_data and (schema_data.get("add_tables") or schema_data.get("add_fields")):
            schema_changes = SchemaChange(
                add_tables=schema_data.get("add_tables", []),
                add_fields=schema_data.get("add_fields", []),
                remove_tables=schema_data.get("remove_tables", []),
                remove_fields=schema_data.get("remove_fields", [])
            )
        
        # Build implementation steps
        implementation_steps = []
        for step_data in analysis.get("implementation_steps", []):
            step = ImplementationStep(
                order=step_data.get("order", 1),
                title=step_data.get("title", "Unknown step"),
                description=step_data.get("description", ""),
                feature=step_data.get("feature", "unknown"),
                files_to_modify=step_data.get("files_to_modify", []),
                hard_requirements=step_data.get("hard_requirements", []),
                acceptance_criteria=step_data.get("acceptance_criteria", []),
                corpus_hints=step_data.get("corpus_hints", [])
            )
            implementation_steps.append(step)
        
        # Sort steps by order
        implementation_steps.sort(key=lambda s: s.order)
        
        # Get corpus examples for the gaps
        corpus_examples = self.get_corpus_examples(corpus_queries)
        
        # Build existing files info
        existing_files = []
        for f in summary.files:
            existing_files.append({
                "path": f.path,
                "description": f.description,
                "key_functions": [fn.name for fn in f.functions],
                "structs": [s.name for s in f.structs]
            })
        
        # Build existing features
        existing_features = (
            summary.features.from_template +
            summary.features.added
        )
        
        # Build known issues
        known_issues = [
            issue.description for issue in summary.known_issues
            if not issue.resolved
        ]
        
        # Add warnings from analysis
        known_issues.extend(analysis.get("warnings", []))
        
        # Standard constraints
        constraints = [
            "GBDK-2020 C compiler",
            "No floating point - integers only",
            "40 sprites max",
            "8KB WRAM limit",
            "VRAM writes only during VBlank",
            "No malloc - static arrays only"
        ]
        
        # Record this in conversation
        schema_change_count = len(schema_changes.add_tables) + len(schema_changes.add_fields) if schema_changes else 0
        self.api.add_conversation_turn(
            project_id=project_id,
            role="system",
            content=f"Designer analyzed request: {len(feature_gaps)} gaps, {len(modifications)} modifications, {schema_change_count} schema changes, {len(implementation_steps)} steps",
            metadata={
                "agent": "designer",
                "action": "analyze",
                "gaps": [g.name for g in feature_gaps],
                "modifications": [m.feature for m in modifications],
                "schema_changes": schema_change_count,
                "implementation_steps": len(implementation_steps),
                "step_titles": [s.title for s in implementation_steps],
                "corpus_examples": len(corpus_examples)
            }
        )
        
        return ContextPackage(
            project_id=project_id,
            project_name=summary.project_name,
            current_state=summary.current_state,
            existing_files=existing_files,
            existing_features=existing_features,
            existing_patterns=summary.patterns,
            user_request=user_request,
            feature_gaps=feature_gaps,
            modifications=modifications,
            schema_changes=schema_changes,
            implementation_steps=implementation_steps,
            corpus_examples=corpus_examples,
            known_issues=known_issues,
            constraints=constraints
        )
    
    def get_relevant_source_files(
        self,
        project_id: str,
        file_paths: list[str]
    ) -> dict[str, str]:
        """
        Read specific source files from the project.
        
        Args:
            project_id: The project ID
            file_paths: List of relative paths (e.g., ["src/game.c"])
            
        Returns:
            Dict mapping path to file content
        """
        project = self.api.get_project(project_id)
        project_path = project.path
        
        contents = {}
        for rel_path in file_paths:
            full_path = project_path / rel_path
            if full_path.exists():
                contents[rel_path] = full_path.read_text()
        
        return contents


def create_designer(
    model: str = "claude-sonnet-4-20250514",
    verbose: bool = False,
    log_callback: callable = None
) -> DesignerAgent:
    """Factory function to create a Designer agent."""
    return DesignerAgent(model=model, verbose=verbose, log_callback=log_callback)
