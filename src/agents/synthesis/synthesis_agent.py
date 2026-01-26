#!/usr/bin/env python3
"""
Synthesis Agent - Converts conversation history into actionable feature requests.

This agent uses Haiku for cost-efficient conversation summarization.
It's a lightweight, single-purpose agent that:
1. Takes conversation turns (user/assistant messages)
2. Synthesizes them into a clear feature request
3. Returns a concise, actionable summary for the Coder

Using Haiku instead of Sonnet/Opus saves ~90% on synthesis costs.
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path

import anthropic

# Load environment
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# Default to Haiku for cost efficiency
DEFAULT_MODEL = "claude-3-5-haiku-20241022"


@dataclass
class SynthesisResult:
    """Result of conversation synthesis."""
    success: bool
    synthesized_request: str
    turn_count: int
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "synthesized_request": self.synthesized_request,
            "turn_count": self.turn_count,
            "error": self.error
        }


class SynthesisAgent:
    """
    Lightweight agent for synthesizing conversation into feature requests.
    
    Uses Haiku by default for cost efficiency - this is a simple summarization
    task that doesn't require deep reasoning.
    """
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        verbose: bool = False
    ):
        """
        Initialize the synthesis agent.
        
        Args:
            model: Model to use (default: Haiku for cost efficiency)
            verbose: Print debug info
        """
        self.model = model
        self.verbose = verbose
        self.client = anthropic.Anthropic()
    
    def _log(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[Synthesis] {message}")
    
    def synthesize_conversation(
        self,
        conversation_turns: list[dict],
        project_context: Optional[str] = None,
        max_turns: int = 15
    ) -> SynthesisResult:
        """
        Synthesize conversation turns into a single feature request.
        
        Args:
            conversation_turns: List of conversation turns with 'role' and 'content'
            project_context: Optional context about the project (name, features, etc.)
            max_turns: Maximum number of recent turns to include
            
        Returns:
            SynthesisResult with the synthesized request
        """
        if not conversation_turns:
            return SynthesisResult(
                success=False,
                synthesized_request="",
                turn_count=0,
                error="No conversation turns provided"
            )
        
        # Take only the most recent turns
        recent_turns = conversation_turns[-max_turns:]
        turn_count = len(recent_turns)
        
        self._log(f"Synthesizing {turn_count} conversation turns...")
        
        # Build conversation text
        conv_text = "\n".join([
            f"{'User' if t.get('role') == 'user' else 'Assistant'}: {t.get('content', '')}"
            for t in recent_turns
        ])
        
        # Build the synthesis prompt
        context_section = ""
        if project_context:
            context_section = f"\nPROJECT CONTEXT:\n{project_context}\n"
        
        synthesis_prompt = f"""Based on this conversation about a GameBoy game project, synthesize what features the user wants to implement.
{context_section}
CONVERSATION:
{conv_text}

Summarize the key features and changes the user wants in 2-3 sentences that could be used as a feature request.
Focus on ACTIONABLE items that can be coded. Be specific about game mechanics.
Output ONLY the synthesized feature request, nothing else."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": synthesis_prompt}]
            )
            
            synthesized_request = response.content[0].text.strip()
            
            self._log(f"Synthesized: {synthesized_request[:80]}...")
            
            return SynthesisResult(
                success=True,
                synthesized_request=synthesized_request,
                turn_count=turn_count
            )
            
        except Exception as e:
            self._log(f"Synthesis failed: {e}")
            return SynthesisResult(
                success=False,
                synthesized_request="",
                turn_count=turn_count,
                error=str(e)
            )
    
    def synthesize_from_turns(
        self,
        turns: list,
        project_context: Optional[str] = None
    ) -> SynthesisResult:
        """
        Convenience method that accepts turn objects with .role and .content attributes.
        
        Args:
            turns: List of turn objects (e.g., from project.conversation)
            project_context: Optional context about the project
            
        Returns:
            SynthesisResult with the synthesized request
        """
        # Convert turn objects to dicts
        conversation_turns = [
            {"role": t.role, "content": t.content}
            for t in turns
            if hasattr(t, 'role') and hasattr(t, 'content')
        ]
        
        return self.synthesize_conversation(
            conversation_turns=conversation_turns,
            project_context=project_context
        )


def create_synthesis_agent(
    model: str = DEFAULT_MODEL,
    verbose: bool = False
) -> SynthesisAgent:
    """Factory function to create a synthesis agent."""
    return SynthesisAgent(model=model, verbose=verbose)
