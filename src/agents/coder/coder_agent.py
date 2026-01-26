"""
Coder Agent - Implements code changes based on ContextPackage from Designer.

The Coder agent:
1. Receives a ContextPackage with minimal, targeted context
2. Implements changes based on identified feature gaps
3. Outputs file modifications (complete files)
4. Triggers summary regeneration after changes
"""

import json
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import anthropic

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
    
    def _stream_message(self, system: str, prompt: str, max_tokens: int = 32768) -> dict:
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
    
    def _implement_steps(
        self,
        context,
        project_path: Path,
        reviewer_feedback: str = None
    ) -> CoderResult:
        """
        Implement changes step-by-step.
        
        Each step:
        1. Gets focused context for just that step
        2. Calls Claude to implement
        3. Builds and validates
        4. If successful, moves to next step
        5. If fails after retries, stops
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
        
        for step in steps:
            self._log("step", f"Step {step.order}/{total_steps}: {step.title}")
            
            # Implement this step
            step_result = self._implement_single_step(
                context, step, project_path,
                reviewer_feedback if step.order == 1 else None  # Only apply reviewer feedback to first step
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
        reviewer_feedback: str = None
    ) -> CoderResult:
        """
        Implement a single step with retries.
        """
        # Read current file contents (fresh for each step)
        current_files = self._read_project_files(project_path)
        
        # Log file selection for cost visibility
        header_files = [f for f in current_files.keys() if f.endswith('.h')]
        impl_files = [f for f in current_files.keys() if f.endswith('.c')]
        files_to_modify = step.files_to_modify if step.files_to_modify else impl_files
        c_files_sent = [f for f in files_to_modify if f.endswith('.c')]
        
        target_files = ", ".join(files_to_modify[:3]) + ("..." if len(files_to_modify) > 3 else "")
        self._log("info", f"   📁 Target: {target_files}")
        
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            if attempt > 1:
                self._log("info", f"   🔄 Retry {attempt}/{self.max_retries}")
            
            self._log("info", f"   🤖 Calling Claude...")
            
            # Build step-focused prompt
            prompt = self._build_step_prompt(context, step, current_files, last_error, reviewer_feedback)
            
            try:
                # Call Claude with streaming (avoids timeout errors on long requests)
                response = self._stream_message(DEV_AGENT_INSTRUCTIONS, prompt)
                
                response_text = response["text"]
                
                # Check if response was truncated (stop_reason will be 'max_tokens' if hit limit)
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
                    
                    # Extract just the error line for logging
                    error_lines = [l for l in (last_error or "").split('\n') if 'error:' in l.lower()]
                    error_preview = error_lines[0][:80] if error_lines else "Build failed"
                    self._log("warning", f"   ⚠️ {error_preview}")
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
                    # Update current_files with what we wrote (for retry context)
                    for fc in files_changed:
                        current_files[fc.path] = fc.content
                    
                    if self.verbose:
                        error_preview = last_error[:200] if last_error else "Unknown error"
                        print(f"[Coder] Build failed: {error_preview}...")
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
    
    def _build_step_prompt(
        self,
        context,
        step,  # ImplementationStep  
        current_files: dict[str, str],
        last_error: Optional[str],
        reviewer_feedback: Optional[str] = None
    ) -> str:
        """Build a focused prompt for a single implementation step."""
        parts = []
        
        # On retry with reviewer feedback, use lightweight context (skip corpus examples)
        if reviewer_feedback:
            parts.append(self._build_retry_context(context, step, reviewer_feedback))
        else:
            # Use step-focused context from ContextPackage (includes corpus examples)
            parts.append(context.to_step_context(step))
        
        # Separate header files (.h) from implementation files (.c)
        header_files = {k: v for k, v in current_files.items() if k.endswith('.h')}
        impl_files = {k: v for k, v in current_files.items() if k.endswith('.c')}
        
        # Determine which .c files to show (selective) - headers always shown
        files_to_modify = step.files_to_modify if step.files_to_modify else list(impl_files.keys())
        c_files_to_show = [f for f in files_to_modify if f.endswith('.c')]
        
        # Always include ALL header files (they contain API contracts, are small)
        parts.append("\n## Header Files (API contracts)")
        parts.append("All header files for reference. These define the interfaces.")
        for filepath in sorted(header_files.keys()):
            parts.append(f"\n### {filepath}")
            parts.append(f"```c\n{header_files[filepath]}\n```")
        
        # Show only the .c files being modified (implementation details)
        parts.append("\n## Implementation Files to Modify")
        parts.append("These are the files you should modify. Return COMPLETE file contents.")
        for filepath in sorted(c_files_to_show):
            if filepath in impl_files:
                parts.append(f"\n### {filepath}")
                parts.append(f"```c\n{impl_files[filepath]}\n```")
        
        # List other .c files by name only for awareness
        other_c_files = [f for f in impl_files.keys() if f not in c_files_to_show]
        if other_c_files:
            parts.append("\n## Other Implementation Files (not shown)")
            parts.append("These files exist but are not shown. Create new files if needed.")
            parts.append(", ".join(sorted(other_c_files)))
        
        # Reviewer feedback section (already included in retry context, but add emphasis)
        if reviewer_feedback and "REVIEWER FEEDBACK" not in parts[0]:
            parts.append("\n## ⚠️ REVIEWER FEEDBACK - ADDRESS THESE ISSUES!")
            parts.append(reviewer_feedback)
        
        # Previous error
        if last_error:
            parts.append("\n## PREVIOUS BUILD ERROR - FIX THIS!")
            parts.append(f"```\n{last_error[:1500]}\n```")
        
        # Final instruction
        parts.append("\n## Task")
        if reviewer_feedback:
            parts.append("**FIX THE REVIEWER ISSUES** listed above.")
            parts.append("Return complete file contents for the fixed files.")
        else:
            parts.append(f"Implement ONLY this step: **{step.title}**")
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
        
        # Previous error
        if last_error:
            parts.append("\n## PREVIOUS BUILD ERROR - FIX THIS!")
            parts.append(f"```\n{last_error[:2000]}\n```")
        
        # Final instruction
        parts.append("\n## Task")
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
        
        return {
            "success": success,
            "output": result.stdout,
            "error": result.stderr if not success else None
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
