"""Reviewer agents package."""
from .logic_reviewer import LogicReviewer, ReviewResult as LogicReviewResult, LogicIssue, ReviewSeverity
from .code_reviewer import CodeReviewer, ReviewResult, ReviewIssue, Severity, create_reviewer

__all__ = [
    # New diff-based reviewer
    'CodeReviewer',
    'ReviewResult', 
    'ReviewIssue',
    'Severity',
    'create_reviewer',
    
    # Legacy logic reviewer
    'LogicReviewer', 
    'LogicReviewResult', 
    'LogicIssue', 
    'ReviewSeverity'
]
