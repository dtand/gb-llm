#!/usr/bin/env python3
"""
Static Analyzer - Enforces coding standards without LLM.

Checks:
- Doxygen file headers
- Section markers
- Function documentation
- Naming conventions
- Type usage
- Magic numbers
- Include order
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    ERROR = "error"      # Must fix before proceeding
    WARNING = "warning"  # Should fix, but can proceed
    INFO = "info"        # Suggestion only


@dataclass
class Issue:
    """A single code standards issue."""
    file: str
    line: Optional[int]
    severity: Severity
    rule: str
    message: str
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"[{self.severity.value.upper()}] {loc}: {self.rule} - {self.message}"


@dataclass
class AnalysisResult:
    """Result of static analysis."""
    passed: bool
    issues: list[Issue] = field(default_factory=list)
    
    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]
    
    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]
    
    def summary(self) -> str:
        lines = [f"Static Analysis: {'PASSED' if self.passed else 'FAILED'}"]
        lines.append(f"  Errors: {len(self.errors)}, Warnings: {len(self.warnings)}")
        if self.issues:
            lines.append("\nIssues:")
            for issue in self.issues:
                lines.append(f"  {issue}")
        return "\n".join(lines)
    
    def feedback_for_coder(self) -> str:
        """Format issues as feedback for the coder to fix."""
        if not self.issues:
            return ""
        
        lines = ["## Code Standards Violations (MUST FIX)\n"]
        
        # Group by file
        by_file: dict[str, list[Issue]] = {}
        for issue in self.issues:
            by_file.setdefault(issue.file, []).append(issue)
        
        for filepath, issues in by_file.items():
            lines.append(f"### {filepath}")
            for issue in issues:
                loc = f"Line {issue.line}: " if issue.line else ""
                lines.append(f"- {loc}**{issue.rule}** - {issue.message}")
                if issue.suggestion:
                    lines.append(f"  - Fix: {issue.suggestion}")
            lines.append("")
        
        return "\n".join(lines)


class StaticAnalyzer:
    """Analyzes code for standards compliance."""
    
    def __init__(self, strict: bool = False):
        """
        Initialize analyzer.
        
        Args:
            strict: If True, warnings become errors
        """
        self.strict = strict
    
    def analyze(self, files: dict[str, str]) -> AnalysisResult:
        """
        Analyze multiple files for standards compliance.
        
        Args:
            files: Dict of filepath -> content
            
        Returns:
            AnalysisResult with all issues found
        """
        issues = []
        
        for filepath, content in files.items():
            if filepath.endswith('.c') or filepath.endswith('.h'):
                issues.extend(self._analyze_c_file(filepath, content))
        
        # Determine pass/fail
        has_errors = any(i.severity == Severity.ERROR for i in issues)
        has_warnings = any(i.severity == Severity.WARNING for i in issues)
        
        passed = not has_errors and (not self.strict or not has_warnings)
        
        return AnalysisResult(passed=passed, issues=issues)
    
    def _analyze_c_file(self, filepath: str, content: str) -> list[Issue]:
        """Analyze a C source or header file."""
        issues = []
        lines = content.split('\n')
        
        # Check file header
        issues.extend(self._check_file_header(filepath, content))
        
        # Check section markers
        issues.extend(self._check_section_markers(filepath, content))
        
        # Check function documentation
        issues.extend(self._check_function_docs(filepath, lines))
        
        # Check naming conventions
        issues.extend(self._check_naming(filepath, lines))
        
        # Check type usage
        issues.extend(self._check_types(filepath, lines))
        
        # Check for magic numbers
        issues.extend(self._check_magic_numbers(filepath, lines))
        
        # Check include order
        issues.extend(self._check_includes(filepath, lines))
        
        return issues
    
    def _check_file_header(self, filepath: str, content: str) -> list[Issue]:
        """Check for Doxygen file header."""
        issues = []
        
        # Must start with /** comment block containing @file
        header_pattern = r'^/\*\*\s*\n\s*\*\s*@file'
        if not re.match(header_pattern, content):
            issues.append(Issue(
                file=filepath,
                line=1,
                severity=Severity.ERROR,
                rule="doxygen-header",
                message="Missing Doxygen file header",
                suggestion="Add /** @file ... @brief ... */ at top of file"
            ))
            return issues
        
        # Check for required tags
        if '@brief' not in content[:500]:
            issues.append(Issue(
                file=filepath,
                line=1,
                severity=Severity.WARNING,
                rule="doxygen-brief",
                message="Missing @brief in file header",
                suggestion="Add @brief with one-line description"
            ))
        
        return issues
    
    def _check_section_markers(self, filepath: str, content: str) -> list[Issue]:
        """Check for section marker comments."""
        issues = []
        
        # Look for function definitions without preceding section
        # This is a soft check - only warn if file is large and has no markers
        has_markers = '// ====' in content or '/* ====' in content
        line_count = content.count('\n')
        
        if line_count > 50 and not has_markers:
            issues.append(Issue(
                file=filepath,
                line=None,
                severity=Severity.WARNING,
                rule="section-markers",
                message="Large file without section markers",
                suggestion="Add // ============ SECTION NAME ============ comments"
            ))
        
        return issues
    
    def _check_function_docs(self, filepath: str, lines: list[str]) -> list[Issue]:
        """Check that functions have documentation."""
        issues = []
        
        # Simple pattern: function definition not preceded by /** comment
        func_pattern = re.compile(r'^(void|uint8_t|int8_t|uint16_t|int16_t|bool)\s+(\w+)\s*\(')
        
        for i, line in enumerate(lines):
            match = func_pattern.match(line.strip())
            if match:
                func_name = match.group(2)
                
                # Skip if it's main
                if func_name == 'main':
                    continue
                
                # Check if previous non-empty line is end of doc comment
                has_doc = False
                for j in range(i - 1, max(0, i - 5), -1):
                    prev = lines[j].strip()
                    if prev == '*/':
                        has_doc = True
                        break
                    if prev and not prev.startswith('//') and not prev.startswith('*'):
                        break
                
                if not has_doc:
                    issues.append(Issue(
                        file=filepath,
                        line=i + 1,
                        severity=Severity.WARNING,
                        rule="function-doc",
                        message=f"Function '{func_name}' missing documentation",
                        suggestion="Add /** @brief ... */ before function"
                    ))
        
        return issues
    
    def _check_naming(self, filepath: str, lines: list[str]) -> list[Issue]:
        """Check naming conventions."""
        issues = []
        
        for i, line in enumerate(lines):
            # Check #define names are UPPER_SNAKE
            define_match = re.match(r'#define\s+([a-z_][a-z0-9_]*)\s', line)
            if define_match:
                name = define_match.group(1)
                if not name.isupper():
                    issues.append(Issue(
                        file=filepath,
                        line=i + 1,
                        severity=Severity.WARNING,
                        rule="naming-define",
                        message=f"#define '{name}' should be UPPER_SNAKE_CASE",
                        suggestion=f"Rename to '{name.upper()}'"
                    ))
            
            # Check function names are snake_case (not camelCase)
            func_match = re.match(r'(void|uint\d+_t|int\d+_t|bool)\s+([a-zA-Z_]\w*)\s*\(', line.strip())
            if func_match:
                name = func_match.group(2)
                if re.search(r'[a-z][A-Z]', name):  # camelCase detected
                    snake = re.sub(r'([a-z])([A-Z])', r'\1_\2', name).lower()
                    issues.append(Issue(
                        file=filepath,
                        line=i + 1,
                        severity=Severity.WARNING,
                        rule="naming-function",
                        message=f"Function '{name}' should be snake_case",
                        suggestion=f"Rename to '{snake}'"
                    ))
        
        return issues
    
    def _check_types(self, filepath: str, lines: list[str]) -> list[Issue]:
        """Check for proper fixed-width type usage."""
        issues = []
        
        # Patterns for forbidden types
        forbidden = [
            (r'\bunsigned\s+char\b', 'uint8_t'),
            (r'\bsigned\s+char\b', 'int8_t'),
            (r'\bunsigned\s+int\b', 'uint16_t'),
            (r'\b(?<!u)int\s+(?!main|8_t|16_t|32_t)', 'int8_t or int16_t'),
        ]
        
        for i, line in enumerate(lines):
            # Skip comments
            if line.strip().startswith('//') or line.strip().startswith('*'):
                continue
            
            for pattern, replacement in forbidden:
                if re.search(pattern, line):
                    issues.append(Issue(
                        file=filepath,
                        line=i + 1,
                        severity=Severity.WARNING,
                        rule="type-usage",
                        message=f"Use fixed-width types from <stdint.h>",
                        suggestion=f"Use {replacement} instead"
                    ))
                    break
        
        return issues
    
    def _check_magic_numbers(self, filepath: str, lines: list[str]) -> list[Issue]:
        """Check for magic numbers that should be constants."""
        issues = []
        
        # Numbers that are probably magic (exclude common ones like 0, 1, 2)
        magic_pattern = re.compile(r'[=<>+\-*/&|]\s*(\d{2,})\b')
        
        # Skip these contexts
        skip_patterns = [
            r'#define',      # In a define (defining the constant)
            r'0x[0-9a-fA-F]+', # Hex literals (often intentional)
            r'//',           # Comments
            r'\*\s',         # Doc comments
        ]
        
        for i, line in enumerate(lines):
            # Skip certain lines
            if any(re.search(p, line) for p in skip_patterns):
                continue
            
            for match in magic_pattern.finditer(line):
                num = int(match.group(1))
                # Skip small numbers and common values
                if num < 10 or num in [16, 32, 64, 128, 255, 256]:
                    continue
                
                issues.append(Issue(
                    file=filepath,
                    line=i + 1,
                    severity=Severity.INFO,
                    rule="magic-number",
                    message=f"Magic number {num} should be a named constant",
                    suggestion=f"Add #define MEANINGFUL_NAME {num}"
                ))
        
        return issues
    
    def _check_includes(self, filepath: str, lines: list[str]) -> list[Issue]:
        """Check include order: system headers, then local headers."""
        issues = []
        
        system_includes = []
        local_includes = []
        
        for i, line in enumerate(lines):
            sys_match = re.match(r'#include\s+<(.+)>', line)
            local_match = re.match(r'#include\s+"(.+)"', line)
            
            if sys_match:
                system_includes.append((i, sys_match.group(1)))
            elif local_match:
                local_includes.append((i, local_match.group(1)))
        
        # Check that all system includes come before local includes
        if system_includes and local_includes:
            last_system = max(i for i, _ in system_includes)
            first_local = min(i for i, _ in local_includes)
            
            if last_system > first_local:
                issues.append(Issue(
                    file=filepath,
                    line=last_system + 1,
                    severity=Severity.INFO,
                    rule="include-order",
                    message="System includes should come before local includes",
                    suggestion="Move #include <...> before #include \"...\""
                ))
        
        # Check that gb/gb.h comes first
        if system_includes:
            first_include = system_includes[0][1]
            if first_include != 'gb/gb.h' and any(h == 'gb/gb.h' for _, h in system_includes):
                issues.append(Issue(
                    file=filepath,
                    line=system_includes[0][0] + 1,
                    severity=Severity.INFO,
                    rule="include-order",
                    message="<gb/gb.h> should be the first include",
                    suggestion="Move #include <gb/gb.h> to first position"
                ))
        
        # CRITICAL: sprites.c must include game.h for SPRITE_* defines
        if filepath.endswith('sprites.c'):
            local_headers = [h for _, h in local_includes]
            if 'game.h' not in local_headers:
                issues.append(Issue(
                    file=filepath,
                    line=1,
                    severity=Severity.ERROR,
                    rule="missing-include",
                    message="sprites.c MUST include game.h for SPRITE_* index defines",
                    suggestion='Add #include "game.h" after system includes'
                ))
        
        return issues


# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python static_analyzer.py <file.c> [file2.c ...]")
        sys.exit(1)
    
    analyzer = StaticAnalyzer(strict=False)
    
    files = {}
    for filepath in sys.argv[1:]:
        path = Path(filepath)
        if path.exists():
            files[filepath] = path.read_text()
    
    result = analyzer.analyze(files)
    print(result.summary())
    
    sys.exit(0 if result.passed else 1)
