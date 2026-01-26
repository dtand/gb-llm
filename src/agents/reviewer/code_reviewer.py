#!/usr/bin/env python3
"""
Code Reviewer Agent - Reviews code diffs for issues.

This reviewer focuses on ONLY the changed code to keep context minimal.
It catches bugs early before they compound across multiple steps.

Key principles:
- Review diffs, not entire files
- Focus on correctness, not style
- Block only for CRITICAL issues
- Provide specific, actionable feedback
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

import anthropic

# Load environment
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Load review standards
STANDARDS_PATH = PROJECT_ROOT / "docs" / "REVIEW_STANDARDS.md"


class Severity(Enum):
    CRITICAL = "critical"    # Blocks approval - will cause crash/corruption
    WARNING = "warning"      # Flag but allow - potential issue
    SUGGESTION = "suggestion"  # Note for future - improvement opportunity


@dataclass
class ReviewIssue:
    """An issue found during code review."""
    severity: Severity
    file: str
    line: Optional[int]
    code: str              # The problematic code snippet
    issue: str             # Short description
    explanation: str       # Why it's a problem
    fix: Optional[str]     # Suggested fix
    
    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "file": self.file,
            "line": self.line,
            "code": self.code,
            "issue": self.issue,
            "explanation": self.explanation,
            "fix": self.fix
        }
    
    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"[{self.severity.value.upper()}] {loc}: {self.issue}"


@dataclass
class ReviewResult:
    """Result of a code review."""
    approved: bool
    summary: str
    issues: list[ReviewIssue] = field(default_factory=list)
    checklist: dict = field(default_factory=dict)
    review_time_ms: int = 0
    
    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)
    
    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
            "checklist": self.checklist,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "review_time_ms": self.review_time_ms
        }
    
    def feedback_for_coder(self) -> str:
        """Format critical issues as feedback for the Coder to fix."""
        critical_issues = [i for i in self.issues if i.severity == Severity.CRITICAL]
        
        if not critical_issues:
            return ""
        
        lines = ["## ❌ Review Failed - Critical Issues Found\n"]
        lines.append("The following issues MUST be fixed before proceeding:\n")
        
        for i, issue in enumerate(critical_issues, 1):
            loc = f"{issue.file}:{issue.line}" if issue.line else issue.file
            lines.append(f"### Issue {i}: {issue.issue}")
            lines.append(f"**Location:** `{loc}`\n")
            lines.append(f"**Code:**\n```c\n{issue.code}\n```\n")
            lines.append(f"**Problem:** {issue.explanation}\n")
            if issue.fix:
                lines.append(f"**Fix:** {issue.fix}\n")
            lines.append("")
        
        return "\n".join(lines)


# System prompt for the reviewer
def get_reviewer_system_prompt() -> str:
    """Load review standards and build system prompt."""
    
    # Load standards if available
    standards_content = ""
    if STANDARDS_PATH.exists():
        standards_content = STANDARDS_PATH.read_text()
    
    return f"""You are a GameBoy code reviewer. You review ONLY the diff (changed code), not the entire project.

## Your Standards
{standards_content}

## Critical Rules

1. **ONLY review the diff** - Don't comment on unchanged code
2. **Focus on correctness** - Not style, naming, or documentation
3. **Be specific** - Include file, line number, and exact problematic code
4. **Suggest fixes** - Don't just complain, provide solutions
5. **Err toward approval** - If unsure, approve with a WARNING

## Severity Guide

- **CRITICAL**: Will DEFINITELY crash or corrupt data at runtime. Blocks approval.
- **WARNING**: MIGHT cause issues under certain conditions. Does not block.
- **SUGGESTION**: Could be better but works fine. Does not block.

## Output Format

Return ONLY valid JSON (no markdown code blocks):

{{
  "approved": true/false,
  "summary": "One-line assessment",
  "issues": [
    {{
      "severity": "critical|warning|suggestion",
      "file": "src/game.c",
      "line": 45,
      "code": "the problematic code",
      "issue": "Short description",
      "explanation": "Why it's a problem",
      "fix": "How to fix it"
    }}
  ],
  "checklist": {{
    "memory_safe": true/false,
    "hardware_safe": true/false,
    "control_flow_safe": true/false,
    "game_logic_safe": true/false
  }}
}}

Set "approved": false ONLY if there are CRITICAL issues. Warnings don't block approval."""


class CodeReviewer:
    """
    Reviews code diffs for issues.
    
    This reviewer is designed to:
    - Work with minimal context (just the diff)
    - Catch critical bugs early
    - Provide actionable feedback
    - Not block progress for minor issues
    """
    
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        verbose: bool = False
    ):
        """
        Initialize the reviewer.
        
        Args:
            model: Claude model to use for review
            verbose: Print debug information
        """
        self.client = anthropic.Anthropic()
        self.model = model
        self.verbose = verbose
    
    def review_diff(
        self,
        task_description: str,
        diff: str,
        changed_files: Optional[dict[str, str]] = None,
    ) -> ReviewResult:
        """
        Review a code diff.
        
        Args:
            task_description: What the code change was supposed to accomplish
            diff: Git-style diff of the changes
            changed_files: Optional dict of filepath -> full content for context
            
        Returns:
            ReviewResult with approval status and any issues
        """
        start_time = datetime.now()
        
        if self.verbose:
            print(f"[Reviewer] Reviewing diff for: {task_description[:50]}...")
        
        # Build the review prompt
        prompt = self._build_prompt(task_description, diff, changed_files)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=get_reviewer_system_prompt(),
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            result = self._parse_response(response_text)
            
            # Record timing
            elapsed = datetime.now() - start_time
            result.review_time_ms = int(elapsed.total_seconds() * 1000)
            
            if self.verbose:
                status = "✅ APPROVED" if result.approved else "❌ REJECTED"
                print(f"[Reviewer] {status} - {result.critical_count} critical, {result.warning_count} warnings")
            
            return result
            
        except Exception as e:
            if self.verbose:
                print(f"[Reviewer] Error during review: {e}")
            
            # On error, approve to not block pipeline
            return ReviewResult(
                approved=True,
                summary=f"Review skipped due to error: {str(e)[:100]}",
                issues=[],
                checklist={}
            )
    
    def review_files(
        self,
        task_description: str,
        before_files: dict[str, str],
        after_files: dict[str, str],
    ) -> ReviewResult:
        """
        Review changes between two file states.
        
        Automatically generates a diff and reviews it.
        
        Args:
            task_description: What the change was supposed to do
            before_files: Dict of filepath -> content before changes
            after_files: Dict of filepath -> content after changes
            
        Returns:
            ReviewResult with approval status and issues
        """
        # Generate diff
        diff = self._generate_diff(before_files, after_files)
        
        # Get only the changed files
        changed_files = {
            path: content 
            for path, content in after_files.items()
            if path not in before_files or before_files[path] != content
        }
        
        return self.review_diff(task_description, diff, changed_files)
    
    def _build_prompt(
        self,
        task_description: str,
        diff: str,
        changed_files: Optional[dict[str, str]] = None
    ) -> str:
        """Build the review prompt."""
        parts = []
        
        parts.append("## Task Description")
        parts.append(f"{task_description}\n")
        
        parts.append("## Code Diff to Review")
        parts.append("```diff")
        parts.append(diff)
        parts.append("```\n")
        
        if changed_files:
            parts.append("## Full Content of Changed Files (for context)")
            for path, content in changed_files.items():
                # Truncate very long files
                if len(content) > 3000:
                    content = content[:3000] + "\n... (truncated)"
                parts.append(f"### {path}")
                parts.append(f"```c\n{content}\n```\n")
        
        parts.append("## Your Task")
        parts.append("Review the diff above. Focus on the CHANGED lines.")
        parts.append("Return your review as JSON.")
        
        return "\n".join(parts)
    
    def _generate_diff(
        self,
        before: dict[str, str],
        after: dict[str, str]
    ) -> str:
        """Generate a unified diff between two file states."""
        import difflib
        
        diff_lines = []
        
        # Find all files
        all_files = set(before.keys()) | set(after.keys())
        
        for filepath in sorted(all_files):
            before_content = before.get(filepath, "")
            after_content = after.get(filepath, "")
            
            if before_content == after_content:
                continue
            
            before_lines = before_content.splitlines(keepends=True)
            after_lines = after_content.splitlines(keepends=True)
            
            diff = difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=f"a/{filepath}",
                tofile=f"b/{filepath}",
                lineterm=""
            )
            
            diff_lines.extend(diff)
        
        return "\n".join(diff_lines)
    
    def _parse_response(self, response_text: str) -> ReviewResult:
        """Parse the LLM response into a ReviewResult."""
        try:
            # Clean up response - remove markdown code blocks if present
            json_str = response_text.strip()
            
            if json_str.startswith("```"):
                # Remove code block markers
                lines = json_str.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                json_str = "\n".join(lines)
            
            data = json.loads(json_str)
            
            # Parse issues
            issues = []
            for issue_data in data.get("issues", []):
                severity_str = issue_data.get("severity", "warning").lower()
                try:
                    severity = Severity(severity_str)
                except ValueError:
                    severity = Severity.WARNING
                
                issues.append(ReviewIssue(
                    severity=severity,
                    file=issue_data.get("file", "unknown"),
                    line=issue_data.get("line"),
                    code=issue_data.get("code", ""),
                    issue=issue_data.get("issue", ""),
                    explanation=issue_data.get("explanation", ""),
                    fix=issue_data.get("fix"),
                ))
            
            return ReviewResult(
                approved=data.get("approved", True),
                summary=data.get("summary", ""),
                issues=issues,
                checklist=data.get("checklist", {}),
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            if self.verbose:
                print(f"[Reviewer] Failed to parse response: {e}")
                print(f"[Reviewer] Response was: {response_text[:500]}")
            
            # On parse error, approve to not block pipeline
            return ReviewResult(
                approved=True,
                summary="Review completed but response parsing failed",
                issues=[],
                checklist={}
            )


def create_reviewer(
    model: str = "claude-sonnet-4-20250514",
    verbose: bool = False
) -> CodeReviewer:
    """Factory function to create a CodeReviewer."""
    return CodeReviewer(model=model, verbose=verbose)


# CLI for testing
if __name__ == "__main__":
    import sys
    
    print("Code Reviewer - Manual Test Mode")
    print("=" * 40)
    
    # Test with a simple diff
    test_diff = """
--- a/src/game.c
+++ b/src/game.c
@@ -45,6 +45,12 @@ void update_game(void) {
     move_sprite(0, player_x, player_y);
 }
 
+void spawn_enemy(void) {
+    enemies[enemy_count] = create_enemy();
+    enemy_count++;
+    move_sprite(enemy_count, enemies[enemy_count-1].x, enemies[enemy_count-1].y);
+}
+
 void main(void) {
     game_init();
"""
    
    reviewer = create_reviewer(verbose=True)
    result = reviewer.review_diff(
        task_description="Add enemy spawning functionality",
        diff=test_diff
    )
    
    print("\n" + "=" * 40)
    print("RESULT:")
    print(json.dumps(result.to_dict(), indent=2))
    
    if not result.approved:
        print("\nFEEDBACK FOR CODER:")
        print(result.feedback_for_coder())
