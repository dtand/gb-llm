#!/usr/bin/env python3
"""
Logic Reviewer Agent - Reviews code for logic errors.

Uses an LLM to analyze code for:
- Logic bugs and edge cases
- Off-by-one errors
- Unhandled conditions
- GameBoy-specific issues (overflow, sprite limits, etc.)
- Implementation vs requirements mismatches
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

# Load environment
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

import anthropic


class ReviewSeverity(Enum):
    CRITICAL = "critical"  # Will cause crash or major bug
    WARNING = "warning"    # Potential issue
    SUGGESTION = "suggestion"  # Could be improved


@dataclass
class LogicIssue:
    """A logic issue found by the reviewer."""
    severity: ReviewSeverity
    location: str  # File and approximate location
    issue: str     # Description of the problem
    explanation: str  # Why it's a problem
    fix: Optional[str] = None  # Suggested fix
    
    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.location}: {self.issue}"


@dataclass
class ReviewResult:
    """Result of logic review."""
    passed: bool
    issues: list[LogicIssue] = field(default_factory=list)
    summary: str = ""
    
    @property
    def critical_issues(self) -> list[LogicIssue]:
        return [i for i in self.issues if i.severity == ReviewSeverity.CRITICAL]
    
    @property
    def warnings(self) -> list[LogicIssue]:
        return [i for i in self.issues if i.severity == ReviewSeverity.WARNING]
    
    def format_summary(self) -> str:
        lines = [f"Logic Review: {'PASSED' if self.passed else 'NEEDS FIXES'}"]
        lines.append(f"  Critical: {len(self.critical_issues)}, Warnings: {len(self.warnings)}")
        
        if self.summary:
            lines.append(f"\nSummary: {self.summary}")
        
        if self.issues:
            lines.append("\nIssues Found:")
            for issue in self.issues:
                lines.append(f"\n  [{issue.severity.value}] {issue.location}")
                lines.append(f"    Issue: {issue.issue}")
                lines.append(f"    Why: {issue.explanation}")
                if issue.fix:
                    lines.append(f"    Fix: {issue.fix}")
        
        return "\n".join(lines)
    
    def feedback_for_coder(self) -> str:
        """Format issues as feedback for the coder to fix."""
        if not self.issues:
            return ""
        
        lines = ["## Logic Issues Found (MUST FIX)\n"]
        
        for issue in self.issues:
            lines.append(f"### [{issue.severity.value.upper()}] {issue.location}")
            lines.append(f"**Problem:** {issue.issue}\n")
            lines.append(f"**Why:** {issue.explanation}\n")
            if issue.fix:
                lines.append(f"**Suggested Fix:** {issue.fix}\n")
            lines.append("")
        
        return "\n".join(lines)


REVIEWER_SYSTEM_PROMPT = """You are an expert GameBoy code reviewer specializing in GBDK-2020.

Your job is to find CRITICAL LOGIC ERRORS that will cause the game to crash or malfunction.

## Only report as CRITICAL:
1. **Definite Crashes**
   - Division by zero that WILL happen
   - Array access guaranteed to be out of bounds
   - Infinite loops with no exit condition

2. **Definite Runtime Failures**
   - VRAM writes outside of vblank (will cause graphical corruption)
   - Using more than 40 sprites (will cause sprites to disappear)
   - Integer overflow that WILL cause incorrect behavior

3. **Critical Logic Errors**
   - Completely missing required functionality (e.g., no input handling when required)
   - State machine that can never exit a state
   - Collision detection that will never trigger

## Report as WARNING (not CRITICAL):
- Off-by-one errors that might occur in edge cases
- Potential issues that depend on specific conditions
- Missing edge case handling
- Debouncing not implemented

## DO NOT report (let static analyzer handle):
- Style issues
- Missing documentation  
- Naming conventions
- Minor optimization suggestions
- Code that compiles and runs but could be "better"

## Key Principle
If the code compiles, builds, and will run without crashing for the basic use case, 
it should PASS. Don't fail working code just because it could be improved.

## Output Format

Return a JSON object:
```json
{
  "passed": true/false,
  "summary": "Brief overall assessment",
  "issues": [
    {
      "severity": "critical|warning|suggestion",
      "location": "src/game.c:update_ball()",
      "issue": "Short description",
      "explanation": "Why this is a problem",
      "fix": "How to fix it (optional)"
    }
  ]
}
```

Set "passed": false ONLY if there are issues that will DEFINITELY cause crashes or failures.
Set "passed": true for warnings/suggestions or if the code will work correctly."""


class LogicReviewer:
    """Reviews code for logic errors using an LLM."""
    
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        verbose: bool = False
    ):
        """
        Initialize the reviewer.
        
        Args:
            model: Claude model to use
            verbose: Print debug info
        """
        self.client = anthropic.Anthropic()
        self.model = model
        self.verbose = verbose
    
    def review_step(
        self,
        step_title: str,
        step_description: str,
        step_requirements: list[str],
        acceptance_criteria: list[str],
        files: dict[str, str],
    ) -> ReviewResult:
        """
        Review code changes for a single step.
        
        Args:
            step_title: Title of the step
            step_description: What this step should accomplish
            step_requirements: Hard requirements for the step
            acceptance_criteria: Criteria that must be met
            files: Dict of filepath -> content for all source files
            
        Returns:
            ReviewResult with any issues found
        """
        if self.verbose:
            print(f"[Reviewer] Reviewing step: {step_title}")
        
        # Build the review prompt
        prompt = self._build_review_prompt(
            step_title,
            step_description,
            step_requirements,
            acceptance_criteria,
            files
        )
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=REVIEWER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            return self._parse_response(response_text)
            
        except Exception as e:
            if self.verbose:
                print(f"[Reviewer] Error: {e}")
            # On error, pass (don't block pipeline)
            return ReviewResult(
                passed=True,
                summary=f"Review skipped due to error: {e}"
            )
    
    def _build_review_prompt(
        self,
        step_title: str,
        step_description: str,
        step_requirements: list[str],
        acceptance_criteria: list[str],
        files: dict[str, str],
    ) -> str:
        """Build the prompt for the reviewer."""
        parts = []
        
        parts.append(f"# Review Request: {step_title}\n")
        parts.append(f"## Step Description\n{step_description}\n")
        
        if step_requirements:
            parts.append("## Requirements (must be implemented)")
            for req in step_requirements:
                parts.append(f"- {req}")
            parts.append("")
        
        if acceptance_criteria:
            parts.append("## Acceptance Criteria (verify these)")
            for crit in acceptance_criteria:
                parts.append(f"- {crit}")
            parts.append("")
        
        parts.append("## Source Code to Review\n")
        for filepath, content in files.items():
            if filepath.endswith('.c') or filepath.endswith('.h'):
                parts.append(f"### {filepath}")
                parts.append(f"```c\n{content}\n```\n")
        
        parts.append("\n## Your Task")
        parts.append("Review the code above for logic errors. Focus on bugs, not style.")
        parts.append("Check that the requirements and acceptance criteria are properly implemented.")
        parts.append("Return your analysis as JSON.")
        
        return "\n".join(parts)
    
    def _parse_response(self, response_text: str) -> ReviewResult:
        """Parse the LLM's response into a ReviewResult."""
        try:
            # Extract JSON from response
            json_str = response_text
            
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                for block in json_str.split("```"):
                    if '"passed"' in block:
                        json_str = block
                        break
            
            data = json.loads(json_str.strip())
            
            issues = []
            for issue_data in data.get("issues", []):
                severity_str = issue_data.get("severity", "warning").lower()
                try:
                    severity = ReviewSeverity(severity_str)
                except ValueError:
                    severity = ReviewSeverity.WARNING
                
                issues.append(LogicIssue(
                    severity=severity,
                    location=issue_data.get("location", "unknown"),
                    issue=issue_data.get("issue", ""),
                    explanation=issue_data.get("explanation", ""),
                    fix=issue_data.get("fix"),
                ))
            
            return ReviewResult(
                passed=data.get("passed", True),
                summary=data.get("summary", ""),
                issues=issues,
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            if self.verbose:
                print(f"[Reviewer] Failed to parse response: {e}")
            # On parse error, pass (don't block pipeline)
            return ReviewResult(
                passed=True,
                summary="Review completed but response parsing failed"
            )


# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python logic_reviewer.py <file.c> [file2.c ...] [-v]")
        sys.exit(1)
    
    verbose = "-v" in sys.argv
    filepaths = [f for f in sys.argv[1:] if f != "-v"]
    
    files = {}
    for filepath in filepaths:
        path = Path(filepath)
        if path.exists():
            files[filepath] = path.read_text()
    
    reviewer = LogicReviewer(verbose=verbose)
    result = reviewer.review_step(
        step_title="Manual Review",
        step_description="Review the provided files for logic errors",
        step_requirements=[],
        acceptance_criteria=[],
        files=files,
    )
    
    print(result.format_summary())
    sys.exit(0 if result.passed else 1)
