"""
Project context management module.

Provides tools for generating, reading, and updating project summaries
that give agents a complete picture of a project's current state.
"""

from .summary_generator import generate_summary, SummaryGenerator
from .schemas import ProjectSummary, FileInfo, StructInfo, FunctionInfo

__all__ = [
    'generate_summary',
    'SummaryGenerator', 
    'ProjectSummary',
    'FileInfo',
    'StructInfo',
    'FunctionInfo'
]
