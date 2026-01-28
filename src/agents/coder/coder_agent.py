"""
Coder Agent - Implements code changes based on ContextPackage from Designer.

The Coder agent uses a two-phase approach to minimize token usage:

Phase 1 (Analysis):
  - Receives step description + symbol index (compact code map)
  - Analyzes which files are needed for the step
  - Returns list of files to request

Phase 2 (Implementation):
  - Receives only the requested files
  - Implements the changes
  - Returns complete file contents
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import anthropic

from ..context.symbol_index import load_symbol_index, symbols_to_prompt

# Model for Phase 1 file selection (cheaper, faster)
PHASE1_MODEL = "claude-3-5-haiku-20241022"

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PROJECTS_DIR = PROJECT_ROOT / "games" / "projects"

# Load developer agent instructions from markdown file
DEV_AGENT_PATH = PROJECT_ROOT / "docs" / "DEV_AGENT.md"
DEV_AGENT_INSTRUCTIONS = ""
if DEV_AGENT_PATH.exists():
    DEV_AGENT_INSTRUCTIONS = DEV_AGENT_PATH.read_text()
else:
    # Fallback minimal instructions if file missing
    DEV_AGENT_INSTRUCTIONS = """You are a GBDK-2020 GameBoy developer.
Output ONLY a JSON code block with complete file contents.
No explanatory text before or after the JSON."""

# System prompt for Phase 1: file selection
FILE_SELECTOR_PROMPT = """You are analyzing a GameBoy codebase to determine which files need to be modified for a specific task.

You will receive:
1. A description of the step to implement
2. A symbol index showing all files, their functions, structs, and relationships
3. A call graph showing function dependencies

Your job is to identify which SOURCE FILES (.c files) need to be read and potentially modified.

RULES:
- Headers (.h files) will ALWAYS be provided - don't request them
- Only request .c files you actually need to see or modify
- Consider the call graph - if modifying function X, you may need files that call X
- For new features, request files where integration code needs to be added
- Be conservative - request only what's truly necessary

Output a JSON object:
```json
{
  "files_needed": ["src/game.c", "src/enemies.c"],
  "reasoning": "Brief explanation of why each file is needed"
}
```"""


@dataclass
class FileChange:
    """A single file change."""
    path: str
    content: str
    change_type: str = "modified"  # "created" | "modified" | "deleted"


@dataclass
class CoderResult:
    """Result from the Coder agent."""
    success: bool
    files_changed: list[FileChange] = field(default_factory=list)
    changes_made: list[str] = field(default_factory=list)
    features_implemented: list[str] = field(default_factory=list)
    steps_completed: int = 0
    total_steps: int = 0
    build_success: bool = False
    build_error: Optional[str] = None
    error: Optional[str] = None


class CoderAgent:
    """
    Coder agent that works with ContextPackage from Designer.
    
    Implements changes step-by-step based on the Designer's implementation plan,
    building and validating after each step to avoid context overload.
    """
    
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_retries: int = 3,
        verbose: bool = False,
        log_callback: callable = None
    ):
        """
        Initialize the Coder agent.
        
        Args:
            model: Claude model to use
            max_retries: Max retry attempts on build failure per step
            verbose: Print debug info
            log_callback: Optional callback(level, message) for log messages
        """
        self.client = anthropic.Anthropic()
        self.model = model
        self.log_callback = log_callback
        self.log_callback = log_callback
        self.max_retries = max_retries
        self.verbose = verbose
    
    def _log(self, level: str, message: str):
        """Log a message to console and callback."""
        if self.verbose:
            print(f"[Coder] {message}")
        if self.log_callback:
            try:
                self.log_callback(level, message)
            except Exception:
                pass
    
    def _stream_message(
        self, system: str, prompt: str, max_tokens: int = 32768, model: str = None
    ) -> dict:
        """
        Call Claude API with streaming to avoid timeout errors.
        
        Args:
            model: Override model (e.g., Haiku for Phase 1). Uses self.model if None.
        
        Returns dict with 'text' (response content) and 'stop_reason'.
        """
        response_text = ""
        stop_reason = None
        use_model = model or self.model
        
        with self.client.messages.stream(
            model=use_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                response_text += text
            # Get the final message for stop_reason
            final_message = stream.get_final_message()
            stop_reason = final_message.stop_reason
        
        return {"text": response_text, "stop_reason": stop_reason}
    
    def implement(
        self,
        context,  # ContextPackage from Designer
        project_path: Path,
        reviewer_feedback: str = None
    ) -> CoderResult:
        """
        Implement changes step-by-step based on the ContextPackage.
        
        If the context has implementation_steps, we iterate through them one at a time.
        Otherwise, we fall back to implementing all gaps at once (legacy behavior).
        
        Args:
            context: ContextPackage with project state, feature gaps, and implementation steps
            project_path: Path to the project directory
            reviewer_feedback: Optional feedback from Reviewer on previous attempt
            
        Returns:
            CoderResult with changes made and build status
        """
        # Check if we have implementation steps
        steps = getattr(context, 'implementation_steps', [])
        
        if steps:
            return self._implement_steps(context, project_path, reviewer_feedback)
        else:
            # Legacy: implement all at once (for simple requests)
            return self._implement_all(context, project_path, reviewer_feedback)
    
    def implement_direct(
        self,
        project_path: Path,
        user_request: str,
        attached_files: list[str] = None
    ) -> CoderResult:
        """
        Dev mode: Single-step implementation without Designer.
        
        User plays the designer role - their request goes directly to the Coder.
        Uses two-phase approach (Haiku for file selection, Sonnet for implementation).
        
        Args:
            project_path: Path to the project directory
            user_request: The user's direct request (replaces Designer's step description)
            attached_files: Optional list of file paths to always include (user-pinned)
            
        Returns:
            CoderResult with changes made, build status, and summary
        """
        self._log("info", "🔧 Dev Mode: Direct implementation")
        self._log("info", f"   Request: {user_request[:80]}...")
        
        # Load symbol index
        symbols = load_symbol_index(project_path)
        
        # Read all files
        all_files = self._read_project_files(project_path)
        header_files = {k: v for k, v in all_files.items() if k.endswith('.h')}
        impl_files = {k: v for k, v in all_files.items() if k.endswith('.c')}
        
        self._log("info", f"   📊 Symbol index: {len(impl_files)} .c, {len(header_files)} .h")
        
        # Phase 1: Determine which files are needed using Haiku
        self._log("info", "   🔍 Phase 1: Analyzing files needed...")
        files_needed = self._select_files_for_direct_request(
            user_request, symbols, attached_files
        )
        
        # Always include headers + selected .c files + user-attached files
        selected_impl_files = {k: v for k, v in impl_files.items() if k in files_needed}
        
        # Add any attached files the user explicitly requested
        if attached_files:
            for af in attached_files:
                if af in impl_files and af not in selected_impl_files:
                    selected_impl_files[af] = impl_files[af]
                    self._log("info", f"   📎 User attached: {af}")
        
        if not selected_impl_files:
            self._log("warning", "   ⚠️ No files selected, using all")
            selected_impl_files = impl_files
        else:
            self._log("info", f"   📁 Selected: {', '.join(selected_impl_files.keys())}")
        
        # Combine headers + selected impl files
        files_for_coding = {**header_files, **selected_impl_files}
        
        last_error = None
        
        # Phase 2: Implement with Sonnet
        for attempt in range(1, self.max_retries + 1):
            if attempt > 1:
                self._log("info", f"   🔄 Retry {attempt}/{self.max_retries}")
                # On retry, expand to include error-mentioned files
                if last_error:
                    error_files = self._extract_files_from_error(last_error, impl_files)
                    for ef in error_files:
                        if ef not in files_for_coding:
                            files_for_coding[ef] = impl_files[ef]
                            self._log("info", f"   📁 Added from error: {ef}")
            
            self._log("info", "   🤖 Phase 2: Implementing...")
            
            # Build prompt for direct request
            prompt = self._build_direct_prompt(user_request, files_for_coding, last_error)
            
            try:
                response = self._stream_message(DEV_AGENT_INSTRUCTIONS, prompt)
                response_text = response["text"]
                
                if response["stop_reason"] == 'max_tokens':
                    self._log("warning", "   ⚠️ Response truncated (token limit)")
                    last_error = "Response was truncated. Try a more focused request."
                    continue
                
                # Parse response
                result = self._parse_response(response_text)
                
                if not result.get("files"):
                    last_error = "Failed to parse file changes from response"
                    self._log("warning", "   ⚠️ Parse failed")
                    continue
                
                # Apply changes
                files_changed = []
                for filepath, content in result["files"].items():
                    full_path = project_path / filepath
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    change_type = "created" if not full_path.exists() else "modified"
                    full_path.write_text(content)
                    
                    files_changed.append(FileChange(
                        path=filepath,
                        content=content,
                        change_type=change_type
                    ))
                
                file_names = [fc.path.split('/')[-1] for fc in files_changed]
                self._log("info", f"   📝 Wrote: {', '.join(file_names)}")
                
                # Build
                self._log("info", "   🔨 Building...")
                build_result = self._build_project(project_path)
                
                if not build_result["success"]:
                    last_error = build_result["error"]
                    self._log("warning", "   ⚠️ Build failed")
                    continue
                
                self._log("success", "   ✅ Build passed")
                
                # Generate summary from changes_made
                summary = result.get("summary", "")
                if not summary and result.get("changes_made"):
                    summary = "Changes: " + "; ".join(result["changes_made"][:3])
                
                return CoderResult(
                    success=True,
                    files_changed=files_changed,
                    changes_made=result.get("changes_made", []),
                    features_implemented=["direct_request"],
                    steps_completed=1,
                    total_steps=1,
                    build_success=True,
                    error=summary  # Repurpose error field for summary in success case
                )
                
            except Exception as e:
                last_error = str(e)
                self._log("error", f"   ❌ Error: {e}")
        
        return CoderResult(
            success=False,
            error=last_error,
            build_success=False,
            build_error=last_error
        )
    
    def _select_files_for_direct_request(
        self,
        user_request: str,
        symbols: dict,
        attached_files: list[str] = None
    ) -> list[str]:
        """
        Phase 1 for dev mode: Use Haiku to select files based on user request.
        """
        prompt_parts = []
        
        prompt_parts.append("## User Request")
        prompt_parts.append(user_request)
        prompt_parts.append("")
        
        if attached_files:
            prompt_parts.append("## User-Attached Files (always include these)")
            prompt_parts.append(", ".join(attached_files))
            prompt_parts.append("")
        
        # Symbol index
        prompt_parts.append(symbols_to_prompt(symbols))
        
        # List available .c files
        files_dict = symbols.get("files", {})
        c_files = [f for f in files_dict.keys() if f.endswith('.c')]
        prompt_parts.append("\n## Available .c Files to Request")
        prompt_parts.append(", ".join(sorted(c_files)))
        
        prompt_parts.append("\n## Your Task")
        prompt_parts.append("Based on the user request and symbol index, determine which .c files are needed.")
        prompt_parts.append("Return ONLY the JSON specifying files_needed.")
        
        prompt = "\n".join(prompt_parts)
        
        try:
            # Phase 1 uses Haiku
            response = self._stream_message(
                FILE_SELECTOR_PROMPT, prompt, max_tokens=1024, model=PHASE1_MODEL
            )
            response_text = response["text"]
            
            files_needed = self._parse_file_selection(response_text, c_files)
            return files_needed
            
        except Exception as e:
            self._log("warning", f"   ⚠️ File selection failed: {e}, using all files")
            return c_files
    
    def _build_direct_prompt(
        self,
        user_request: str,
        current_files: dict[str, str],
        last_error: str = None
    ) -> str:
        """Build prompt for direct dev mode implementation."""
        prompt_parts = []
        
        prompt_parts.append("## User Request")
        prompt_parts.append(user_request)
        prompt_parts.append("")
        
        if last_error:
            prompt_parts.append("## Previous Attempt Failed")
            prompt_parts.append(f"Error: {last_error}")
            prompt_parts.append("Fix the error in your implementation.")
            prompt_parts.append("")
        
        prompt_parts.append("## Current Source Files")
        for filepath, content in sorted(current_files.items()):
            prompt_parts.append(f"\n### {filepath}")
            prompt_parts.append(f"```c\n{content}\n```")
        
        prompt_parts.append("\n## Instructions")
        prompt_parts.append("Implement the user's request. Output complete file contents as JSON.")
        prompt_parts.append("Include a 'summary' field with a brief description of what you changed.")
        
        return "\n".join(prompt_parts)
    
    def _implement_steps(
        self,
        context,
        project_path: Path,
        reviewer_feedback: str = None
    ) -> CoderResult:
        """
        Implement changes step-by-step with context passing between steps.
        
        Each step:
        1. Gets focused context for just that step
        2. Receives summary of previous step's changes (for context continuity)
        3. Calls Claude to implement
        4. Builds and validates
        5. If successful, generates summary and moves to next step
        6. If fails after retries, stops
        """
        steps = context.implementation_steps
        total_steps = len(steps)
        
        self._log("info", f"📋 Implementation plan: {total_steps} steps")
        for s in steps:
            self._log("info", f"   {s.order}. {s.title}")
        
        # Send progress start
        self._log("progress", f"0/{total_steps}")
        
        all_files_changed = []
        all_changes_made = []
        all_features_implemented = set()
        previous_step_summary = None  # Track what previous step accomplished
        
        for step in steps:
            self._log("step", f"Step {step.order}/{total_steps}: {step.title}")
            
            # Implement this step, passing previous step summary for context
            step_result = self._implement_single_step(
                context, step, project_path,
                reviewer_feedback if step.order == 1 else None,  # Only apply reviewer feedback to first step
                previous_step_summary
            )
            
            if not step_result.success:
                self._log("error", f"❌ Step {step.order} failed: {step_result.error}")
                return CoderResult(
                    success=False,
                    files_changed=all_files_changed,
                    changes_made=all_changes_made,
                    features_implemented=list(all_features_implemented),
                    steps_completed=step.order - 1,
                    total_steps=total_steps,
                    build_success=False,
                    error=f"Step {step.order} ({step.title}) failed: {step_result.error}"
                )
            
            # Accumulate results
            all_files_changed.extend(step_result.files_changed)
            all_changes_made.extend(step_result.changes_made)
            all_features_implemented.add(step.feature)
            
            # Build summary of this step for next step's context
            files_modified = [fc.path for fc in step_result.files_changed]
            changes_list = step_result.changes_made or [f"Modified {', '.join(files_modified)}"]
            previous_step_summary = f"Step {step.order} ({step.title}):\n" + "\n".join(f"- {c}" for c in changes_list[:5])
            
            # Log progress
            self._log("progress", f"{step.order}/{total_steps}")
            self._log("success", f"✅ Step {step.order} complete")
        
        self._log("success", f"✅ All {total_steps} steps completed!")
        
        return CoderResult(
            success=True,
            files_changed=all_files_changed,
            changes_made=all_changes_made,
            features_implemented=list(all_features_implemented),
            steps_completed=total_steps,
            total_steps=total_steps,
            build_success=True
        )
    
    def _implement_single_step(
        self,
        context,
        step,  # ImplementationStep
        project_path: Path,
        reviewer_feedback: str = None,
        previous_step_summary: str = None
    ) -> CoderResult:
        """
        Implement a single step using two-phase approach:
        
        Phase 1: Analyze symbol index to determine which files are needed
        Phase 2: Request those files and implement the changes
        
        Args:
            context: The ContextPackage from Designer
            step: The specific ImplementationStep to implement
            project_path: Path to the project
            reviewer_feedback: Feedback from reviewer (first step only)
            previous_step_summary: Summary of what was done in previous step
        """
        # Load symbol index (from file if available, otherwise generate)
        symbols = load_symbol_index(project_path)
        
        # Read all files (we'll selectively send them)
        all_files = self._read_project_files(project_path)
        header_files = {k: v for k, v in all_files.items() if k.endswith('.h')}
        impl_files = {k: v for k, v in all_files.items() if k.endswith('.c')}
        
        self._log("info", f"   📊 Symbol index: {len(impl_files)} .c, {len(header_files)} .h")
        
        # Phase 1: Determine which files are needed
        self._log("info", f"   🔍 Phase 1: Analyzing files needed...")
        files_needed = self._select_files_for_step(
            context, step, symbols, previous_step_summary
        )
        
        # Always include headers, but only requested .c files
        selected_impl_files = {k: v for k, v in impl_files.items() if k in files_needed}
        
        # If no files selected, default to all (fallback for edge cases)
        if not selected_impl_files:
            self._log("warning", f"   ⚠️ No files selected, using all")
            selected_impl_files = impl_files
        else:
            self._log("info", f"   📁 Selected: {', '.join(selected_impl_files.keys())}")
        
        # Combine headers + selected impl files
        files_for_coding = {**header_files, **selected_impl_files}
        
        last_error = None
        
        # Phase 2: Implement with selected files
        for attempt in range(1, self.max_retries + 1):
            if attempt > 1:
                self._log("info", f"   🔄 Retry {attempt}/{self.max_retries}")
                # On retry, expand to include error-mentioned files
                if last_error:
                    error_files = self._extract_files_from_error(last_error, impl_files)
                    for ef in error_files:
                        if ef not in files_for_coding:
                            files_for_coding[ef] = impl_files[ef]
                            self._log("info", f"   📁 Added from error: {ef}")
            
            self._log("info", f"   🤖 Phase 2: Implementing...")
            
            # Build prompt with selected files only
            prompt = self._build_step_prompt(
                context, step, files_for_coding, last_error, 
                reviewer_feedback, previous_step_summary
            )
            
            try:
                # Call Claude with streaming
                response = self._stream_message(DEV_AGENT_INSTRUCTIONS, prompt)
                
                response_text = response["text"]
                
                if response["stop_reason"] == 'max_tokens':
                    self._log("warning", "   ⚠️ Response truncated (token limit)")
                    last_error = "Response was truncated - file too large. Try simplifying the change."
                    continue
                
                # Parse response
                result = self._parse_response(response_text)
                
                if not result.get("files"):
                    last_error = "Failed to parse file changes from response"
                    self._log("warning", f"   ⚠️ Parse failed")
                    continue
                
                # Apply changes
                files_changed = []
                for filepath, content in result["files"].items():
                    full_path = project_path / filepath
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    change_type = "created" if not full_path.exists() else "modified"
                    full_path.write_text(content)
                    
                    files_changed.append(FileChange(
                        path=filepath,
                        content=content,
                        change_type=change_type
                    ))
                
                # Log files written
                file_names = [fc.path.split('/')[-1] for fc in files_changed]
                self._log("info", f"   📝 Wrote: {', '.join(file_names)}")
                
                # Build
                self._log("info", f"   🔨 Building...")
                build_result = self._build_project(project_path)
                
                if not build_result["success"]:
                    last_error = build_result["error"]
                    # Update current_files with what we wrote (for retry context)
                    for fc in files_changed:
                        current_files[fc.path] = fc.content
                    
                    # Extract error lines - look for common compiler error patterns
                    # SDCC/GBDK errors often contain: "error", "Error", "undefined", "syntax"
                    error_patterns = ['error', 'undefined', 'syntax', 'expected', 'undeclared', 'conflicting']
                    all_lines = (last_error or "").split('\n')
                    error_lines = [l.strip() for l in all_lines 
                                   if any(p in l.lower() for p in error_patterns) and l.strip()]
                    
                    if error_lines:
                        # Show first few actual error lines
                        error_preview = error_lines[0][:120]
                        self._log("warning", f"   ⚠️ Build failed")
                        for err_line in error_lines[:5]:  # Show up to 5 error lines
                            self._log("warning", f"      {err_line[:120]}")
                        if len(error_lines) > 5:
                            self._log("warning", f"      ... and {len(error_lines) - 5} more error(s)")
                    else:
                        # Fallback: show last non-empty lines of output
                        non_empty = [l.strip() for l in all_lines if l.strip()]
                        self._log("warning", f"   ⚠️ Build failed")
                        for line in non_empty[-5:]:
                            self._log("warning", f"      {line[:120]}")
                    continue
                
                self._log("info", f"   ✅ Build passed")
                
                return CoderResult(
                    success=True,
                    files_changed=files_changed,
                    changes_made=result.get("changes_made", []),
                    features_implemented=[step.feature],
                    build_success=True
                )
                
            except Exception as e:
                last_error = str(e)
                self._log("error", f"   ❌ Error: {e}")
        
        return CoderResult(
            success=False,
            error=last_error,
            build_success=False,
            build_error=last_error
        )
    
    def _implement_all(
        self,
        context,
        project_path: Path,
        reviewer_feedback: str = None
    ) -> CoderResult:
        """
        Legacy implementation: implement all gaps at once.
        Used for simple requests with no implementation_steps.
        """
        if self.verbose:
            print(f"[Coder] Implementing {len(context.feature_gaps)} features (legacy mode)")
            print(f"[Coder] Project: {context.project_name}")
            if reviewer_feedback:
                print(f"[Coder] Has reviewer feedback to address")
        
        # Read current file contents
        current_files = self._read_project_files(project_path)
        
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            if self.verbose:
                print(f"[Coder] Attempt {attempt}/{self.max_retries}")
            
            # Build prompt
            prompt = self._build_prompt(context, current_files, last_error, reviewer_feedback)
            
            try:
                # Call Claude with streaming (avoids timeout errors on long requests)
                response = self._stream_message(DEV_AGENT_INSTRUCTIONS, prompt)
                
                response_text = response["text"]
                
                # Check if response was truncated
                if response["stop_reason"] == 'max_tokens':
                    if self.verbose:
                        print(f"[Coder] WARNING: Response was truncated (hit token limit)")
                    last_error = "Response was truncated - file too large. Try simplifying the change."
                    continue
                
                # Parse response
                result = self._parse_response(response_text)
                
                if not result.get("files"):
                    last_error = "Failed to parse file changes from response"
                    continue
                
                # Apply changes
                files_changed = []
                for filepath, content in result["files"].items():
                    full_path = project_path / filepath
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    change_type = "created" if not full_path.exists() else "modified"
                    full_path.write_text(content)
                    
                    files_changed.append(FileChange(
                        path=filepath,
                        content=content,
                        change_type=change_type
                    ))
                    
                    if self.verbose:
                        print(f"[Coder] {change_type.capitalize()}: {filepath}")
                
                # Build
                build_result = self._build_project(project_path)
                
                if not build_result["success"]:
                    last_error = build_result["error"]
                    # Update files_for_coding with what we wrote (for retry context)
                    for fc in files_changed:
                        files_for_coding[fc.path] = fc.content
                    
                    if self.verbose:
                        # Extract meaningful error lines
                        error_patterns = ['error', 'undefined', 'syntax', 'expected', 'undeclared', 'conflicting']
                        all_lines = (last_error or "").split('\n')
                        error_lines = [l.strip() for l in all_lines 
                                       if any(p in l.lower() for p in error_patterns) and l.strip()]
                        
                        print(f"[Coder] Build failed:")
                        if error_lines:
                            for err_line in error_lines[:10]:
                                print(f"[Coder]    {err_line[:150]}")
                            if len(error_lines) > 10:
                                print(f"[Coder]    ... and {len(error_lines) - 10} more error(s)")
                        else:
                            # Fallback to last lines
                            non_empty = [l.strip() for l in all_lines if l.strip()]
                            for line in non_empty[-5:]:
                                print(f"[Coder]    {line[:150]}")
                    continue
                
                if self.verbose:
                    print(f"[Coder] Build successful!")
                
                return CoderResult(
                    success=True,
                    files_changed=files_changed,
                    changes_made=result.get("changes_made", []),
                    features_implemented=result.get("features_implemented", []),
                    build_success=True
                )
                
            except Exception as e:
                last_error = str(e)
                if self.verbose:
                    print(f"[Coder] Error: {e}")
        
        return CoderResult(
            success=False,
            error=last_error,
            build_success=False,
            build_error=last_error
        )
    
    def _read_project_files(self, project_path: Path) -> dict[str, str]:
        """Read all source files from project."""
        files = {}
        src_path = project_path / "src"
        
        if src_path.exists():
            for f in src_path.glob("*.c"):
                files[f"src/{f.name}"] = f.read_text()
            for f in src_path.glob("*.h"):
                files[f"src/{f.name}"] = f.read_text()
        
        return files
    
    def _select_files_for_step(
        self,
        context,
        step,
        symbols: dict,
        previous_step_summary: Optional[str] = None
    ) -> list[str]:
        """
        Phase 1: Use symbol index to determine which files are needed.
        
        Calls Claude with the symbol index (compact) to get file selection.
        
        Args:
            symbols: Dict loaded from symbols.json
        """
        # Build the file selection prompt
        prompt_parts = []
        
        # Step context
        prompt_parts.append(f"## Step to Implement: {step.title}")
        prompt_parts.append(f"**Description:** {step.description}")
        prompt_parts.append(f"**Feature:** {step.feature}")
        
        if step.hard_requirements:
            prompt_parts.append("\n**Requirements:**")
            for req in step.hard_requirements:
                prompt_parts.append(f"- {req}")
        
        if previous_step_summary:
            prompt_parts.append(f"\n**Previous Step:**\n{previous_step_summary}")
        
        prompt_parts.append("")
        
        # Symbol index - use the prompt formatter
        prompt_parts.append(symbols_to_prompt(symbols))
        
        # List available .c files explicitly
        files_dict = symbols.get("files", {})
        c_files = [f for f in files_dict.keys() if f.endswith('.c')]
        prompt_parts.append("\n## Available .c Files to Request")
        prompt_parts.append(", ".join(sorted(c_files)))
        
        prompt_parts.append("\n## Your Task")
        prompt_parts.append("Based on the step description and symbol index, determine which .c files are needed.")
        prompt_parts.append("Return ONLY the JSON specifying files_needed.")
        
        prompt = "\n".join(prompt_parts)
        
        try:
            # Phase 1 uses Haiku (faster, cheaper) with small max_tokens
            response = self._stream_message(
                FILE_SELECTOR_PROMPT, prompt, max_tokens=1024, model=PHASE1_MODEL
            )
            response_text = response["text"]
            
            # Parse the file selection response
            files_needed = self._parse_file_selection(response_text, c_files)
            
            return files_needed
            
        except Exception as e:
            self._log("warning", f"   ⚠️ File selection failed: {e}, using all files")
            return c_files
    
    def _parse_file_selection(self, response_text: str, available_files: list[str]) -> list[str]:
        """Parse the file selection response from Phase 1."""
        try:
            # Extract JSON from response
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0]
            else:
                # Try to find raw JSON
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end]
                else:
                    return available_files
            
            result = json.loads(json_str.strip())
            files_needed = result.get("files_needed", [])
            
            # Validate that requested files exist
            valid_files = [f for f in files_needed if f in available_files]
            
            # Log reasoning if verbose
            if self.verbose and "reasoning" in result:
                print(f"[Coder] File selection reasoning: {result['reasoning']}")
            
            return valid_files if valid_files else available_files
            
        except (json.JSONDecodeError, KeyError) as e:
            if self.verbose:
                print(f"[Coder] File selection parse error: {e}")
            return available_files
    
    def _extract_files_from_error(self, error: str, available_files: dict[str, str]) -> list[str]:
        """Extract file paths mentioned in build errors."""
        # Error format: "src/game.c:214: error 26: ..."
        error_file_pattern = r'(src/[a-zA-Z0-9_]+\.c):\d+:'
        error_files = set(re.findall(error_file_pattern, error))
        
        # Only return files that exist in available_files
        return [f for f in error_files if f in available_files]
    
    def _build_step_prompt(
        self,
        context,
        step,  # ImplementationStep  
        current_files: dict[str, str],
        last_error: Optional[str],
        reviewer_feedback: Optional[str] = None,
        previous_step_summary: Optional[str] = None
    ) -> str:
        """Build a focused prompt for a single implementation step.
        
        The Coder now sees ALL project files and decides what to modify based on
        the step description and the actual code. No pre-determined file targeting.
        """
        parts = []
        
        # On retry with reviewer feedback, use lightweight context
        if reviewer_feedback:
            parts.append(self._build_retry_context(context, step, reviewer_feedback))
        else:
            # Use step-focused context from ContextPackage
            parts.append(context.to_step_context(step))
        
        # Add previous step summary if available (for context continuity)
        if previous_step_summary:
            parts.append("\n## Previous Step Summary")
            parts.append("Here's what was accomplished in the previous step:")
            parts.append(previous_step_summary)
            parts.append("")
        
        # Separate header files (.h) from implementation files (.c)
        header_files = {k: v for k, v in current_files.items() if k.endswith('.h')}
        impl_files = {k: v for k, v in current_files.items() if k.endswith('.c')}
        
        # Add code inventory - explicitly list what exists and MUST be preserved
        parts.append("\n## ⚠️ EXISTING CODE INVENTORY (MUST PRESERVE)")
        parts.append("The following functions and features ALREADY EXIST and MUST NOT be removed:")
        parts.append("")
        
        # Extract function names from each .c file  
        for filepath in sorted(impl_files.keys()):
            content = impl_files[filepath]
            # Simple regex to find function definitions
            func_pattern = r'^(?:void|uint8_t|int8_t|uint16_t|int16_t|int|char|const\s+\w+)\s+(\w+)\s*\([^)]*\)\s*{'
            funcs = re.findall(func_pattern, content, re.MULTILINE)
            if funcs:
                parts.append(f"**{filepath}**: `{'`, `'.join(funcs)}`")
        parts.append("")
        parts.append("**Do NOT delete any of these functions unless the task explicitly says to remove them.**")
        parts.append("")
        
        # Always include ALL header files (they contain API contracts, are small)
        parts.append("\n## Header Files (API contracts)")
        parts.append("All header files for reference. These define the interfaces.")
        for filepath in sorted(header_files.keys()):
            parts.append(f"\n### {filepath}")
            parts.append(f"```c\\n{header_files[filepath]}\\n```")
        
        # Show ALL implementation files - Coder decides what needs to change
        parts.append("\n## Implementation Files")
        parts.append("All implementation files in the project. Analyze the code and determine which files")
        parts.append("need to be modified to accomplish this step. Return COMPLETE file contents for any files you modify.")
        for filepath in sorted(impl_files.keys()):
            parts.append(f"\n### {filepath}")
            parts.append(f"```c\n{impl_files[filepath]}\n```")
        
        # Reviewer feedback section (already included in retry context, but add emphasis)
        if reviewer_feedback and "REVIEWER FEEDBACK" not in parts[0]:
            parts.append("\n## ⚠️ REVIEWER FEEDBACK - ADDRESS THESE ISSUES!")
            parts.append(reviewer_feedback)
        
        # Previous error - give prominent placement and specific guidance
        if last_error:
            parts.append("\n## ⛔ BUILD ERROR - YOUR PREVIOUS CODE FAILED TO COMPILE")
            parts.append("")
            parts.append("The code you generated has compilation errors. You MUST fix these before proceeding.")
            parts.append("")
            parts.append("### Error Output:")
            parts.append(f"```\n{last_error[:2000]}\n```")
            parts.append("")
            parts.append("### How to fix:")
            parts.append("1. Read each error message carefully - note the FILE and LINE NUMBER")
            parts.append("2. Common GBDK/SDCC compile errors:")
            parts.append("   - 'undefined identifier' → Missing #include, typo in name, or declaration missing")
            parts.append("   - 'syntax error' → Missing semicolon, brace, or parenthesis")
            parts.append("   - 'conflicting types' → Function signature doesn't match declaration in .h file")
            parts.append("   - 'expected' → Usually a missing token like ';' or ')'")
            parts.append("3. Linker errors (ASlink 'Undefined Global'):")
            parts.append("   - This means a function is CALLED but never IMPLEMENTED")
            parts.append("   - You must add the function body to a .c file")
            parts.append("   - Check which .c file should contain the implementation")
            parts.append("4. Fix the EXACT errors shown - do not make unrelated changes")
            parts.append("5. Ensure .h declarations match .c implementations exactly")
            parts.append("")
        
        # Final instruction with strong preservation emphasis
        parts.append("\n## Task")
        if last_error:
            parts.append("**⛔ PRIORITY: FIX THE BUILD ERRORS** shown above.")
            parts.append("Carefully analyze each error message and fix the issues in your code.")
            parts.append("Return the COMPLETE corrected file contents.")
            parts.append("")
            parts.append("**⚠️ PRESERVE ALL EXISTING CODE** - only fix the specific errors, don't remove unrelated code.")
        elif reviewer_feedback:
            parts.append("**FIX THE REVIEWER ISSUES** listed above.")
            parts.append("Return complete file contents for the fixed files.")
            parts.append("")
            parts.append("**⚠️ PRESERVE ALL EXISTING CODE** - only fix the specific issues mentioned.")
        else:
            parts.append(f"Implement ONLY this step: **{step.title}**")
            parts.append("")
            parts.append("**⚠️ CRITICAL - CODE PRESERVATION:**")
            parts.append("- KEEP all existing functions, variables, and logic NOT related to this step")
            parts.append("- ADD new code to implement the feature - don't REPLACE existing code")
            parts.append("- If modifying a function, preserve all other functions in that file")
            parts.append("- Only change the minimum code necessary for this specific step")
            parts.append("")
            parts.append("Return complete file contents for any files you modify (including headers if needed).")
            parts.append("Do NOT implement features from other steps - stay focused on this one.")
        
        return "\n".join(parts)
    
    def _build_retry_context(
        self,
        context,
        step,
        reviewer_feedback: str
    ) -> str:
        """
        Build lightweight context for retry attempts.
        
        Skips corpus examples and focuses on:
        - What the step was trying to do
        - The reviewer feedback to address
        """
        sections = []
        
        # Minimal project context
        sections.append(f"## Retry: Fixing Review Issues for {context.project_name}")
        sections.append("")
        
        # What we were trying to do (brief)
        sections.append("## Original Task")
        sections.append(f"**Step:** {step.title}")
        sections.append(f"**Description:** {step.description}")
        sections.append("")
        
        # The critical part: reviewer feedback
        sections.append("## ⚠️ REVIEWER FEEDBACK - FIX THESE ISSUES!")
        sections.append(reviewer_feedback)
        sections.append("")
        
        # Hard requirements still apply
        if step.hard_requirements:
            sections.append("### Rules Still Apply")
            for req in step.hard_requirements:
                sections.append(f"- {req}")
            sections.append("")
        
        return "\n".join(sections)
    
    def _build_prompt(
        self,
        context,  # ContextPackage
        current_files: dict[str, str],
        last_error: Optional[str],
        reviewer_feedback: Optional[str] = None
    ) -> str:
        """Build the prompt for Claude (legacy mode)."""
        parts = []
        
        # Use the ContextPackage's formatted context
        parts.append(context.to_prompt_context())
        
        # Current file contents
        parts.append("\n## Current File Contents")
        parts.append("These are the COMPLETE current files. Modify and return complete files.")
        
        for filepath, content in sorted(current_files.items()):
            parts.append(f"\n### {filepath}")
            parts.append(f"```c\n{content}\n```")
        
        # Reviewer feedback from previous attempt
        if reviewer_feedback:
            parts.append("\n## ⚠️ REVIEWER FEEDBACK - ADDRESS THESE ISSUES!")
            parts.append("Your previous implementation had critical issues that must be fixed:")
            parts.append(reviewer_feedback)
        
        # Previous error - give prominent placement and specific guidance
        if last_error:
            parts.append("\n## ⛔ BUILD ERROR - YOUR PREVIOUS CODE FAILED TO COMPILE")
            parts.append("")
            parts.append("The code you generated has compilation errors. You MUST fix these before proceeding.")
            parts.append("")
            parts.append("### Error Output:")
            parts.append(f"```\n{last_error[:2000]}\n```")
            parts.append("")
            parts.append("### How to fix:")
            parts.append("1. Read each error message carefully - note the FILE and LINE NUMBER")
            parts.append("2. Common GBDK/SDCC compile errors:")
            parts.append("   - 'undefined identifier' → Missing #include, typo in name, or declaration missing")
            parts.append("   - 'syntax error' → Missing semicolon, brace, or parenthesis")
            parts.append("   - 'conflicting types' → Function signature doesn't match declaration in .h file")
            parts.append("   - 'expected' → Usually a missing token like ';' or ')'")
            parts.append("3. Linker errors (ASlink 'Undefined Global'):")
            parts.append("   - This means a function is CALLED but never IMPLEMENTED")
            parts.append("   - You must add the function body to a .c file")
            parts.append("   - Check which .c file should contain the implementation")
            parts.append("4. Fix the EXACT errors shown - do not make unrelated changes")
            parts.append("5. Ensure .h declarations match .c implementations exactly")
            parts.append("")
        
        # Final instruction
        parts.append("\n## Task")
        if last_error:
            parts.append("**⛔ PRIORITY: FIX THE BUILD ERRORS** shown above.")
            parts.append("Carefully analyze each error message and fix the issues in your code.")
            parts.append("Return the COMPLETE corrected file contents.")
        else:
            parts.append("Implement the requested features. Return complete file contents for any files you modify.")
            parts.append("Only modify files that need changes. Preserve existing functionality.")
        
        return "\n".join(parts)
    
    def _parse_response(self, response_text: str) -> dict:
        """Parse Claude's response, extracting JSON even with preamble text."""
        try:
            # Find JSON in response - handle preamble text before ```json
            json_str = response_text
            
            if "```json" in json_str:
                # Extract content between ```json and closing ```
                after_marker = json_str.split("```json", 1)[1]
                if "```" in after_marker:
                    json_str = after_marker.split("```", 1)[0]
                else:
                    # No closing ```, take the rest
                    json_str = after_marker
            elif "```" in json_str:
                # Try to find a code block containing "files"
                for block in json_str.split("```"):
                    stripped = block.strip()
                    if stripped.startswith("{") and '"files"' in stripped:
                        json_str = stripped
                        break
            else:
                # No code blocks, try to find raw JSON
                if "{" in json_str:
                    start = json_str.index("{")
                    json_str = json_str[start:]
            
            result = json.loads(json_str.strip())
            return result
            
        except json.JSONDecodeError as e:
            if self.verbose:
                print(f"[Coder] JSON parse failed: {e}")
                # Show where the JSON was truncated
                if "```json" in response_text:
                    try:
                        extracted = response_text.split("```json", 1)[1]
                        if "```" in extracted:
                            extracted = extracted.split("```", 1)[0]
                        print(f"[Coder] Extracted JSON length: {len(extracted)}")
                        print(f"[Coder] JSON end preview: ...{extracted[-300:]}")
                    except:
                        pass
            return self._fallback_parse(response_text)
    
    def _fallback_parse(self, response_text: str) -> dict:
        """Fallback parser for when JSON fails."""
        import re
        
        files = {}
        
        # Look for file headers and code blocks
        pattern = r'###\s*(src/[^\s]+\.[ch])\s*\n```c?\n(.*?)```'
        matches = re.findall(pattern, response_text, re.DOTALL)
        
        for filepath, content in matches:
            files[filepath.strip()] = content.strip()
        
        return {"files": files} if files else {}
    
    def _build_project(self, project_path: Path) -> dict:
        """Build the project using make."""
        result = subprocess.run(
            ["make", "rebuild"],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        
        success = result.returncode == 0
        
        # Combine stdout and stderr for error reporting
        # GBDK/SDCC compilers often output errors to stdout
        combined_output = ""
        if result.stdout:
            combined_output += result.stdout
        if result.stderr:
            combined_output += "\n" + result.stderr if combined_output else result.stderr
        
        return {
            "success": success,
            "output": result.stdout,
            "error": combined_output.strip() if not success else None
        }


# Backwards compatibility aliases
CoderAgentV2 = CoderAgent


def create_coder(
    model: str = "claude-sonnet-4-20250514",
    verbose: bool = False,
    log_callback: callable = None
) -> CoderAgent:
    """Factory function to create a Coder agent."""
    return CoderAgent(model=model, verbose=verbose, log_callback=log_callback)
