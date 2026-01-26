"""
Summary generator for project context.

Parses project source files and generates a comprehensive summary
that agents can use to understand the project's current state.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from .schemas import (
    ProjectSummary, FileInfo, StructInfo, FunctionInfo, 
    ConstantInfo, KnownIssue, FeatureSet
)


class CParser:
    """Simple C source file parser for extracting structs, functions, constants."""
    
    # Regex patterns
    INCLUDE_PATTERN = re.compile(r'#include\s*[<"]([^>"]+)[>"]')
    DEFINE_PATTERN = re.compile(r'#define\s+(\w+)\s+(.+?)(?:\s*//\s*(.*))?$', re.MULTILINE)
    STRUCT_PATTERN = re.compile(
        r'(?:typedef\s+)?struct\s+(\w+)?\s*\{([^}]+)\}\s*(\w+)?;',
        re.DOTALL
    )
    TYPEDEF_STRUCT_PATTERN = re.compile(
        r'typedef\s+struct\s*\{([^}]+)\}\s*(\w+);',
        re.DOTALL
    )
    ENUM_PATTERN = re.compile(
        r'typedef\s+enum\s*\{([^}]+)\}\s*(\w+);',
        re.DOTALL
    )
    FUNCTION_PATTERN = re.compile(
        r'^(\w+(?:\s*\*)?)\s+(\w+)\s*\(([^)]*)\)\s*\{',
        re.MULTILINE
    )
    FUNCTION_DECL_PATTERN = re.compile(
        r'^(\w+(?:\s*\*)?)\s+(\w+)\s*\(([^)]*)\);',
        re.MULTILINE
    )
    DOC_COMMENT_PATTERN = re.compile(
        r'/\*\*\s*\n\s*\*\s*@brief\s+(.+?)\n.*?\*/',
        re.DOTALL
    )
    
    @classmethod
    def parse_file(cls, filepath: str) -> FileInfo:
        """Parse a C source file and extract its components."""
        path = Path(filepath)
        
        try:
            content = path.read_text()
        except Exception as e:
            return FileInfo(
                path=str(path.name),
                description=f"Error reading file: {e}",
                lines=0
            )
        
        lines = content.split('\n')
        line_count = len(lines)
        
        # Extract components
        includes = cls._extract_includes(content)
        constants = cls._extract_constants(content)
        structs = cls._extract_structs(content)
        functions = cls._extract_functions(content, lines)
        
        # Try to extract file description from doc comment
        description = cls._extract_file_description(content)
        
        return FileInfo(
            path=f"src/{path.name}",
            description=description,
            structs=structs,
            functions=functions,
            constants=constants,
            includes=includes,
            lines=line_count
        )
    
    @classmethod
    def _extract_includes(cls, content: str) -> list[str]:
        """Extract #include directives."""
        return cls.INCLUDE_PATTERN.findall(content)
    
    @classmethod
    def _extract_constants(cls, content: str) -> list[ConstantInfo]:
        """Extract #define constants."""
        constants = []
        for match in cls.DEFINE_PATTERN.finditer(content):
            name, value, comment = match.groups()
            # Skip include guards and function-like macros
            if name.endswith('_H') or '(' in value:
                continue
            constants.append(ConstantInfo(
                name=name,
                value=value.strip(),
                comment=comment or ""
            ))
        return constants
    
    @classmethod
    def _extract_structs(cls, content: str) -> list[StructInfo]:
        """Extract struct definitions."""
        structs = []
        
        # Handle typedef struct { ... } Name;
        for match in cls.TYPEDEF_STRUCT_PATTERN.finditer(content):
            body, name = match.groups()
            fields = cls._parse_struct_fields(body)
            structs.append(StructInfo(
                name=name,
                fields=fields,
                description="",
                line_start=content[:match.start()].count('\n') + 1,
                line_end=content[:match.end()].count('\n') + 1
            ))
        
        # Handle typedef enum { ... } Name;
        for match in cls.ENUM_PATTERN.finditer(content):
            body, name = match.groups()
            values = [v.strip().split('=')[0].strip() 
                     for v in body.split(',') if v.strip()]
            structs.append(StructInfo(
                name=name,
                fields=[{"name": v, "type": "enum_value", "comment": ""} for v in values if v],
                description="Enum type",
                line_start=content[:match.start()].count('\n') + 1,
                line_end=content[:match.end()].count('\n') + 1
            ))
        
        return structs
    
    @classmethod
    def _parse_struct_fields(cls, body: str) -> list[dict]:
        """Parse fields from a struct body."""
        fields = []
        # Simple field pattern: type name; or type name; // comment
        field_pattern = re.compile(r'(\w+(?:\s*\*)?)\s+(\w+)(?:\[[\d\w]+\])?;(?:\s*//\s*(.*))?')
        
        for match in field_pattern.finditer(body):
            field_type, name, comment = match.groups()
            fields.append({
                "name": name,
                "type": field_type.strip(),
                "comment": comment or ""
            })
        
        return fields
    
    @classmethod
    def _extract_functions(cls, content: str, lines: list[str]) -> list[FunctionInfo]:
        """Extract function definitions."""
        functions = []
        
        # Find function definitions (with body)
        for match in cls.FUNCTION_PATTERN.finditer(content):
            return_type, name, params = match.groups()
            
            # Skip common false positives
            if name in ('if', 'while', 'for', 'switch'):
                continue
            
            line_start = content[:match.start()].count('\n') + 1
            
            # Find the end of the function (matching braces)
            line_end = cls._find_function_end(content, match.end())
            
            # Parse parameters
            param_list = [p.strip() for p in params.split(',') if p.strip()]
            
            functions.append(FunctionInfo(
                name=name,
                return_type=return_type.strip(),
                parameters=param_list,
                description="",
                line_start=line_start,
                line_end=line_end
            ))
        
        return functions
    
    @classmethod
    def _find_function_end(cls, content: str, start_pos: int) -> int:
        """Find the line number where a function ends."""
        brace_count = 1
        pos = start_pos
        
        while pos < len(content) and brace_count > 0:
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1
        
        return content[:pos].count('\n') + 1
    
    @classmethod
    def _extract_file_description(cls, content: str) -> str:
        """Extract file description from doc comment."""
        # Look for @file and @brief in the header
        brief_match = re.search(r'@brief\s+(.+?)(?:\n|\*)', content)
        if brief_match:
            return brief_match.group(1).strip()
        
        # Look for @game tag
        game_match = re.search(r'@game\s+(.+?)(?:\n|\*)', content)
        if game_match:
            return f"Game: {game_match.group(1).strip()}"
        
        return ""


class SummaryGenerator:
    """Generates project summaries from source files."""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.src_path = self.project_path / "src"
        self.metadata_path = self.project_path / "metadata.json"
        self.plan_path = self.project_path / "plan.json"
        
    def generate(self, template_metadata: Optional[dict] = None) -> ProjectSummary:
        """Generate a complete project summary."""
        # Load existing metadata
        metadata = self._load_metadata()
        plan = self._load_plan()
        
        # Parse all source files
        files = self._parse_source_files()
        
        # Detect patterns in the code
        patterns = self._detect_patterns(files)
        
        # Extract features
        features = self._extract_features(metadata, plan, template_metadata)
        
        # Extract known issues from human feedback
        known_issues = self._extract_known_issues(metadata)
        
        # Determine current state
        current_state = self._determine_state(metadata)
        
        # Build ROM info
        rom_size = self._get_rom_size()
        verification = metadata.get('verification_details') or {}
        checks = verification.get('checks') or []
        build_success = len(checks) > 0 and checks[0].get('status') == 'passed'
        
        return ProjectSummary(
            project_id=metadata.get('id', self.project_path.name),
            project_name=metadata.get('name', 'unknown'),
            description=metadata.get('description', ''),
            template_source=plan.get('template_sample') if plan else None,
            template_name=plan.get('template_sample') if plan else None,
            current_state=current_state,
            features=features,
            files=files,
            patterns=patterns,
            known_issues=known_issues,
            last_build_success=build_success,
            last_build_error=metadata.get('error'),
            rom_size_bytes=rom_size,
            created_at=metadata.get('created_at', ''),
            last_updated=metadata.get('updated_at', ''),
            summary_generated_at=datetime.now().isoformat()
        )
    
    def _load_metadata(self) -> dict:
        """Load project metadata.json."""
        if self.metadata_path.exists():
            return json.loads(self.metadata_path.read_text())
        return {}
    
    def _load_plan(self) -> Optional[dict]:
        """Load project plan.json."""
        if self.plan_path.exists():
            return json.loads(self.plan_path.read_text())
        return None
    
    def _parse_source_files(self) -> list[FileInfo]:
        """Parse all source files in the project."""
        files = []
        
        if not self.src_path.exists():
            return files
        
        c_files = list(self.src_path.glob('*.c'))
        h_files = list(self.src_path.glob('*.h'))
        
        for src_file in sorted(c_files) + sorted(h_files):
            file_info = CParser.parse_file(str(src_file))
            files.append(file_info)
        
        return files
    
    def _detect_patterns(self, files: list[FileInfo]) -> list[str]:
        """Detect code patterns from parsed files."""
        patterns = []
        
        # Collect all struct names, function names, constants
        all_structs = set()
        all_functions = set()
        all_constants = set()
        
        for f in files:
            all_structs.update(s.name for s in f.structs)
            all_functions.update(fn.name for fn in f.functions)
            all_constants.update(c.name for c in f.constants)
        
        # Pattern detection rules
        if 'GameState' in all_structs or 'GameStateType' in all_structs:
            patterns.append('state_machine')
        
        if any('velocity' in c.lower() for c in all_constants):
            patterns.append('physics')
        
        if any('SPRITE_' in c for c in all_constants):
            patterns.append('sprites')
        
        if any('TILE_' in c for c in all_constants):
            patterns.append('tiles')
        
        if 'update_ai' in all_functions or 'ai_' in ' '.join(all_functions).lower():
            patterns.append('ai')
        
        if any('collision' in fn.lower() for fn in all_functions):
            patterns.append('collision')
        
        if any('score' in c.lower() for c in all_constants) or 'update_score' in all_functions:
            patterns.append('scoring')
        
        if any('PADDLE' in c for c in all_constants):
            patterns.append('paddle')
        
        if any('BALL' in c for c in all_constants):
            patterns.append('ball_physics')
        
        if any('GRAVITY' in c for c in all_constants):
            patterns.append('gravity')
        
        if any('JUMP' in c for c in all_constants):
            patterns.append('jumping')
        
        return patterns
    
    def _extract_features(
        self, 
        metadata: dict, 
        plan: Optional[dict],
        template_metadata: Optional[dict]
    ) -> FeatureSet:
        """Extract features from metadata and plan."""
        from_template = []
        added = []
        planned = []
        
        # If we have a template, its features are "from_template"
        if template_metadata:
            from_template = template_metadata.get('features', []) or []
        
        # Features from plan are "added"
        if plan:
            steps = plan.get('steps') or []
            for step in steps:
                features = step.get('features_added') or []
                added.extend(features)
        
        return FeatureSet(
            from_template=from_template,
            added=list(set(added)),  # dedupe
            planned=planned
        )
    
    def _extract_known_issues(self, metadata: dict) -> list[KnownIssue]:
        """Extract known issues from human feedback."""
        issues = []
        
        human_feedback = metadata.get('human_feedback') or []
        for feedback in human_feedback:
            if feedback.get('rating') in ('needs_work', 'broken'):
                issues.append(KnownIssue(
                    description=feedback.get('feedback', ''),
                    severity='critical' if feedback.get('rating') == 'broken' else 'major',
                    source='human_feedback',
                    timestamp=feedback.get('timestamp', ''),
                    resolved=False
                ))
        
        # Check for build errors
        if metadata.get('error'):
            issues.append(KnownIssue(
                description=metadata['error'],
                severity='critical',
                source='build_error',
                timestamp=metadata.get('updated_at', ''),
                resolved=False
            ))
        
        return issues
    
    def _determine_state(self, metadata: dict) -> str:
        """Determine the current project state."""
        status = metadata.get('status', '')
        
        if status == 'completed':
            return 'refined'
        elif status == 'pending_review':
            return 'runs'
        elif status == 'building':
            return 'compiles'
        elif status in ('error', 'build_failed', 'pending'):
            return 'scaffolded'
        else:
            # Check verification
            verification = metadata.get('verification_details') or {}
            checks = verification.get('checks') or []
            if any(c.get('name') == 'Boot Check' and c.get('status') == 'passed' for c in checks):
                return 'runs'
            if any(c.get('name') == 'Compile Check' and c.get('status') == 'passed' for c in checks):
                return 'compiles'
        
        return 'scaffolded'
    
    def _get_rom_size(self) -> int:
        """Get the ROM file size if it exists."""
        build_path = self.project_path / "build"
        if build_path.exists():
            for rom in build_path.glob('*.gb'):
                return rom.stat().st_size
        return 0
    
    def save_summary(self, summary: ProjectSummary, output_path: Optional[str] = None):
        """Save the summary to a JSON file."""
        if output_path is None:
            context_dir = self.project_path / "context"
            context_dir.mkdir(exist_ok=True)
            output_path = context_dir / "summary.json"
        else:
            output_path = Path(output_path)
        
        output_path.write_text(summary.to_json())
        return output_path


def generate_summary(project_path: str, template_metadata: Optional[dict] = None) -> ProjectSummary:
    """
    Convenience function to generate a summary for a project.
    
    Args:
        project_path: Path to the project directory
        template_metadata: Optional metadata from the template this project forked from
        
    Returns:
        ProjectSummary object with complete project context
    """
    generator = SummaryGenerator(project_path)
    return generator.generate(template_metadata)


# CLI support
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.agents.context.summary_generator <project_path>")
        sys.exit(1)
    
    project_path = sys.argv[1]
    generator = SummaryGenerator(project_path)
    summary = generator.generate()
    
    # Save to context/summary.json
    output_path = generator.save_summary(summary)
    print(f"Summary saved to: {output_path}")
    
    # Also print to stdout
    print("\n" + summary.to_json())
