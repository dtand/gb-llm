"""
Synthesis Agent - Lightweight conversation-to-request synthesis.

Uses Haiku for cost-efficient conversation summarization.
"""

from .synthesis_agent import SynthesisAgent, SynthesisResult, create_synthesis_agent

__all__ = ["SynthesisAgent", "SynthesisResult", "create_synthesis_agent"]
