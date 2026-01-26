#!/usr/bin/env python3
"""
Cleanup Agent - Refactors code to improve quality.

This agent runs AFTER the Reviewer approves code, focusing on:
- Removing code duplication
- Extracting magic numbers to constants
- Simplifying complex functions
- Removing dead code

It does NOT change functionality - only improves maintainability.
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

import anthropic

# Load environment
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Load cleanup standards
STANDARDS_PATH = PROJECT_ROOT / "docs" / "CLEANUP_STANDARDS.md"


@dataclass
class CleanupResult:
    """Result of a cleanup pass."""
    success: bool
    changes_made: list[str] = field(default_factory=list)
    files_changed: dict[str, str] = field(default_factory=dict)
    files_created: list[str] = field(default_factory=list)
    improvements: dict = field(default_factory=dict)
    build_success: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "changes_made": self.changes_made,
            "files_changed": list(self.files_changed.keys()),
            "files_created": self.files_created,
            "improvements": self.improvements,
            "build_success": self.build_success,
            "error": self.error
        }


def get_cleanup_system_prompt() -> str:
    """Load cleanup standards and build system prompt."""
    
    standards_content = ""
    if STANDARDS_PATH.exists():
        standards_content = STANDARDS_PATH.read_text()
    
    return f"""You are a GameBoy code cleanup/refactoring agent. Your job is to improve code quality WITHOUT changing functionality.

## Your Standards
{standards_content}

## Critical Rules

1. **PRESERVE FUNCTIONALITY** - The code must work exactly the same after refactoring
2. **SMALL CHANGES** - Make incremental improvements, not rewrites
3. **BUILD MUST PASS** - Any change that breaks compilation is wrong
4. **RESPECT GB LIMITS** - Don't add overhead that hurts performance
5. **SPLIT LARGE FILES** - Files over 300 lines should be split into modules
6. **NEVER SPLIT ASSET FILES** - Keep sprites.c, tiles.c, maps.c, sounds.c intact (UI tools parse these)

## What You Receive
- Current source files (with line counts)
- Current Makefile
- Recent changes made by the Coder

## File Splitting

When splitting a large file (e.g., game.c) into modules:
1. Create new .h file with public interface
2. Create new .c file with implementation
3. Update the original file to #include the new headers
4. Update Makefile SOURCES line to include new .c files

**NEVER split these asset files (even if large):**
- sprites.c / sprites.h - Sprite tile data
- tiles.c / tiles.h - Background tiles
- maps.c / maps.h - Level data
- sounds.c / sounds.h - Audio data

Asset files are parsed by UI tools for visualization.

## What You Output
Return ONLY valid JSON (no markdown code blocks):

{{
  "changes_made": [
    "Split player code from game.c into player.c/player.h",
    "Extracted SCREEN_BOUNDS constants"
  ],
  "files": {{
    "src/game.h": "... complete file contents ...",
    "src/game.c": "... complete file contents ...",
    "src/player.h": "... NEW file contents ...",
    "src/player.c": "... NEW file contents ...",
    "Makefile": "... updated Makefile with new SOURCES ..."
  }},
  "new_files": ["src/player.h", "src/player.c"],
  "improvements": {{
    "files_split": 1,
    "duplication_removed": 0,
    "constants_extracted": 0,
    "functions_simplified": 0
  }}
}}

## If No Cleanup Needed
If the code is already clean, return:
{{
  "changes_made": [],
  "files": {{}},
  "new_files": [],
  "improvements": {{}}
}}

Focus on the most impactful improvements. Prioritize splitting large files."""


class CleanupAgent:
    """
    Cleanup agent that refactors code for improved quality.
    
    Runs after Reviewer, focuses on maintainability without
    changing functionality.
    """
    
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        verbose: bool = False
    ):
        """
        Initialize the Cleanup agent.
        
        Args:
            model: Claude model to use
            verbose: Print debug info
        """
        self.client = anthropic.Anthropic()
        self.model = model
        self.verbose = verbose
    
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
            final_message = stream.get_final_message()
            stop_reason = final_message.stop_reason
        
        return {"text": response_text, "stop_reason": stop_reason}
    
    def cleanup(
        self,
        project_path: Path,
        recent_changes: list[str] = None
    ) -> CleanupResult:
        """
        Run cleanup/refactoring on the project.
        
        Args:
            project_path: Path to the project directory
            recent_changes: List of recent changes made (for context)
            
        Returns:
            CleanupResult with any refactorings applied
        """
        import subprocess
        
        if self.verbose:
            print(f"[Cleanup] Analyzing project for refactoring opportunities...")
        
        # Read current files (source + Makefile)
        current_files = self._read_project_files(project_path)
        makefile_path = project_path / "Makefile"
        original_makefile = None
        if makefile_path.exists():
            original_makefile = makefile_path.read_text()
            current_files["Makefile"] = original_makefile
        
        if not current_files:
            return CleanupResult(
                success=True,
                changes_made=["No source files to cleanup"],
                build_success=True
            )
        
        # Build prompt with line counts
        prompt = self._build_prompt(current_files, project_path, recent_changes)
        
        try:
            # Call Claude with streaming (avoids timeout errors)
            response = self._stream_message(get_cleanup_system_prompt(), prompt)
            
            response_text = response["text"]
            
            # Parse response
            result = self._parse_response(response_text)
            
            if not result.get("files"):
                # No changes needed
                if self.verbose:
                    print("[Cleanup] No refactoring needed")
                return CleanupResult(
                    success=True,
                    changes_made=result.get("changes_made", ["Code is already clean"]),
                    improvements=result.get("improvements", {}),
                    build_success=True
                )
            
            # Track what we're changing
            files_changed = {}
            files_created = result.get("new_files", [])
            
            # Apply changes (both modified and new files)
            for filepath, content in result["files"].items():
                full_path = project_path / filepath
                
                # Create parent directories if needed
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                is_new = not full_path.exists()
                full_path.write_text(content)
                
                if is_new:
                    if self.verbose:
                        print(f"[Cleanup] Created: {filepath}")
                else:
                    files_changed[filepath] = content
                    if self.verbose:
                        print(f"[Cleanup] Modified: {filepath}")
            
            # Verify build still works
            build_result = subprocess.run(
                ["make", "rebuild"],
                cwd=project_path,
                capture_output=True,
                text=True
            )
            
            if build_result.returncode != 0:
                # Rollback ALL changes
                if self.verbose:
                    print("[Cleanup] Build failed, rolling back changes")
                
                # Restore original files
                for filepath, content in current_files.items():
                    (project_path / filepath).write_text(content)
                
                # Delete any newly created files
                for filepath in files_created:
                    new_file = project_path / filepath
                    if new_file.exists():
                        new_file.unlink()
                        if self.verbose:
                            print(f"[Cleanup] Deleted: {filepath}")
                
                return CleanupResult(
                    success=False,
                    error=f"Cleanup broke build: {build_result.stderr[:500]}",
                    build_success=False
                )
            
            if self.verbose:
                print(f"[Cleanup] Successfully applied {len(result.get('changes_made', []))} refactorings")
                if files_created:
                    print(f"[Cleanup] Created {len(files_created)} new files")
            
            return CleanupResult(
                success=True,
                changes_made=result.get("changes_made", []),
                files_changed=files_changed,
                files_created=files_created,
                improvements=result.get("improvements", {}),
                build_success=True
            )
            
        except Exception as e:
            if self.verbose:
                print(f"[Cleanup] Error: {e}")
            return CleanupResult(
                success=False,
                error=str(e),
                build_success=False
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
    
    def _build_prompt(
        self,
        current_files: dict[str, str],
        project_path: Path,
        recent_changes: list[str] = None
    ) -> str:
        """Build the prompt for Claude."""
        parts = []
        
        # Summary of file sizes
        parts.append("## File Size Summary\n")
        parts.append("| File | Lines | Status |")
        parts.append("|------|-------|--------|")
        for filepath, content in sorted(current_files.items()):
            if filepath == "Makefile":
                continue
            line_count = len(content.splitlines())
            status = "⚠️ LARGE - consider splitting" if line_count > 300 else "OK"
            parts.append(f"| {filepath} | {line_count} | {status} |")
        parts.append("")
        
        # Makefile (important for SOURCES)
        if "Makefile" in current_files:
            parts.append("## Current Makefile")
            parts.append("```makefile")
            parts.append(current_files["Makefile"])
            parts.append("```\n")
        
        parts.append("## Source Files\n")
        
        for filepath, content in sorted(current_files.items()):
            if filepath == "Makefile":
                continue
            line_count = len(content.splitlines())
            parts.append(f"### {filepath} ({line_count} lines)")
            parts.append(f"```c\n{content}\n```\n")
        
        if recent_changes:
            parts.append("## Recent Changes")
            parts.append("These changes were just made (be careful refactoring new code):")
            for change in recent_changes:
                parts.append(f"- {change}")
            parts.append("")
        
        parts.append("## Task")
        parts.append("Analyze the code and apply any beneficial refactorings.")
        parts.append("")
        parts.append("**Priority 1: Split large files** - Any file over 300 lines should be split into logical modules.")
        parts.append("**Priority 2: Remove duplication** - Extract repeated code into helper functions.")
        parts.append("**Priority 3: Extract constants** - Replace magic numbers with named constants.")
        parts.append("")
        parts.append("When splitting files:")
        parts.append("1. Create proper header files with include guards")
        parts.append("2. Update #include statements in all affected files")
        parts.append("3. Update the Makefile SOURCES line to include new .c files")
        parts.append("4. List new files in the 'new_files' array")
        parts.append("")
        parts.append("Return complete file contents for ALL files you modify or create.")
        
        return "\n".join(parts)
    
    def _parse_response(self, response_text: str) -> dict:
        """Parse Claude's response."""
        try:
            json_str = response_text
            
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                # Try to find JSON block
                for block in json_str.split("```"):
                    if '"files"' in block or '"changes_made"' in block:
                        json_str = block
                        break
            
            return json.loads(json_str.strip())
            
        except json.JSONDecodeError:
            if self.verbose:
                print("[Cleanup] JSON parse failed")
            return {"files": {}, "changes_made": [], "improvements": {}}


def create_cleanup_agent(
    model: str = "claude-sonnet-4-20250514",
    verbose: bool = False
) -> CleanupAgent:
    """Factory function to create a cleanup agent."""
    return CleanupAgent(model=model, verbose=verbose)
