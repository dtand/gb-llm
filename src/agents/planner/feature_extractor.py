"""
Feature extraction from natural language game descriptions.

Uses keyword matching and pattern recognition to identify required GameBoy features
from user descriptions.
"""

from typing import List, Dict, Set, Tuple
import re


# Keywords that map to features
FEATURE_KEYWORDS = {
    # Graphics
    "sprites": [
        "sprite", "character", "player", "enemy", "ball", "paddle", "object",
        "entity", "actor", "moving", "movable"
    ],
    "backgrounds": [
        "background", "level", "stage", "screen", "field", "arena", "board"
    ],
    "tiles": [
        "tile", "block", "brick", "grid", "cell", "map", "wall", "floor",
        "platform", "terrain"
    ],
    "animation": [
        "animate", "animation", "frame", "cycle", "spin", "rotate", "flash",
        "blink", "walking", "running", "idle"
    ],
    "scrolling": [
        "scroll", "scrolling", "side-scroll", "sidescroll", "endless",
        "infinite", "moving background", "parallax"
    ],
    
    # Input
    "dpad": [
        "move", "movement", "direction", "left", "right", "up", "down",
        "walk", "control", "steer", "navigate"
    ],
    "buttons": [
        "button", "press", "jump", "shoot", "fire", "action", "select",
        "confirm", "a button", "b button", "start"
    ],
    
    # Physics
    "velocity": [
        "speed", "velocity", "fast", "slow", "accelerate", "decelerate",
        "momentum"
    ],
    "gravity": [
        "gravity", "fall", "falling", "jump", "jumping", "platformer",
        "drop", "weight", "arc"
    ],
    "collision_aabb": [
        "collision", "collide", "hit", "touch", "bump", "crash", "contact",
        "intersect", "overlap"
    ],
    "collision_tile": [
        "tile collision", "wall collision", "solid", "passable", "block",
        "brick", "destroy", "break"
    ],
    "bounce": [
        "bounce", "bouncing", "reflect", "ricochet", "rebound", "elastic"
    ],
    
    # Audio
    "sfx": [
        "sound", "sfx", "effect", "beep", "noise", "audio"
    ],
    "music": [
        "music", "song", "tune", "melody", "soundtrack", "bgm", "theme"
    ],
    
    # Data
    "game_state": [
        "score", "points", "lives", "health", "hp", "level", "stage",
        "win", "lose", "game over"
    ],
    "save_sram": [
        "save", "load", "persist", "remember", "continue", "progress",
        "battery", "sram"
    ],
    "highscores": [
        "high score", "highscore", "best", "record", "leaderboard", "top"
    ],
    "rng": [
        "random", "randomize", "procedural", "generate", "spawn", "chance",
        "probability", "luck"
    ],
    
    # Systems
    "ai": [
        "ai", "computer", "cpu", "opponent", "enemy", "chase", "follow",
        "patrol", "behavior", "intelligent", "npc"
    ],
    "state_machine": [
        "state", "menu", "pause", "title", "game over", "screen", "mode",
        "transition"
    ],
}

# Game type patterns that imply multiple features
GAME_TYPE_PATTERNS = {
    r"platformer|platform game": ["sprites", "gravity", "collision_tile", "dpad", "buttons"],
    r"shooter|shoot.?em.?up|shmup": ["sprites", "collision_aabb", "velocity", "buttons", "rng"],
    r"puzzle": ["tiles", "backgrounds", "dpad", "game_state"],
    r"rpg|role.?playing": ["sprites", "tiles", "save_sram", "game_state", "dpad"],
    r"racing|race game": ["sprites", "scrolling", "velocity", "collision_aabb"],
    r"fighting|fighter": ["sprites", "collision_aabb", "animation", "buttons"],
    r"rhythm|music game": ["music", "buttons", "animation"],
    r"breakout|arkanoid|brick.?break": ["sprites", "tiles", "collision_tile", "collision_aabb", "velocity"],
    r"pong|paddle": ["sprites", "collision_aabb", "velocity", "ai", "dpad"],
    r"snake": ["sprites", "collision_tile", "rng", "dpad", "game_state"],
    r"tetris|falling.?block": ["tiles", "collision_tile", "dpad", "buttons", "game_state"],
    r"endless.?runner|runner": ["sprites", "scrolling", "gravity", "collision_aabb", "buttons"],
    r"clicker|idle": ["buttons", "save_sram", "highscores", "game_state"],
}


def extract_features(description: str) -> Dict[str, List[str]]:
    """
    Extract required features from a game description.
    
    Args:
        description: Natural language game description
    
    Returns:
        Dict with:
            - "features": List of identified features
            - "game_type": Detected game type (if any)
            - "confidence": Dict mapping features to confidence levels
            - "keywords_matched": Dict mapping features to matched keywords
    """
    description_lower = description.lower()
    
    # Track results
    features: Set[str] = set()
    confidence: Dict[str, float] = {}
    keywords_matched: Dict[str, List[str]] = {}
    detected_game_type: str = None
    
    # Check for game type patterns first
    for pattern, implied_features in GAME_TYPE_PATTERNS.items():
        if re.search(pattern, description_lower):
            detected_game_type = pattern.split("|")[0].replace("\\", "")
            for feature in implied_features:
                features.add(feature)
                confidence[feature] = confidence.get(feature, 0) + 0.8
    
    # Check individual keywords
    for feature, keywords in FEATURE_KEYWORDS.items():
        matched = []
        for keyword in keywords:
            if keyword in description_lower:
                matched.append(keyword)
        
        if matched:
            features.add(feature)
            keywords_matched[feature] = matched
            # More keyword matches = higher confidence
            confidence[feature] = confidence.get(feature, 0) + min(len(matched) * 0.3, 1.0)
    
    # Normalize confidence scores
    for feature in confidence:
        confidence[feature] = min(confidence[feature], 1.0)
    
    # Sort features by confidence
    sorted_features = sorted(features, key=lambda f: confidence.get(f, 0), reverse=True)
    
    return {
        "features": sorted_features,
        "game_type": detected_game_type,
        "confidence": confidence,
        "keywords_matched": keywords_matched
    }


def get_primary_features(extraction_result: Dict, threshold: float = 0.5) -> List[str]:
    """Get features above a confidence threshold."""
    return [
        f for f in extraction_result["features"]
        if extraction_result["confidence"].get(f, 0) >= threshold
    ]


def get_feature_summary(extraction_result: Dict) -> str:
    """Generate a human-readable summary of extracted features."""
    lines = []
    
    if extraction_result["game_type"]:
        lines.append(f"Detected game type: {extraction_result['game_type']}")
    
    lines.append("\nRequired features:")
    for feature in extraction_result["features"]:
        conf = extraction_result["confidence"].get(feature, 0)
        keywords = extraction_result["keywords_matched"].get(feature, [])
        keyword_str = f" (matched: {', '.join(keywords)})" if keywords else ""
        lines.append(f"  - {feature}: {conf:.0%} confidence{keyword_str}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test feature extraction
    test_descriptions = [
        "A platformer where you collect coins and avoid enemies",
        "Pong with two paddles and a bouncing ball",
        "An endless runner with obstacles to jump over",
        "A breakout clone where you break bricks with a ball",
        "A simple clicker game that saves your high score",
    ]
    
    print("=== Feature Extraction Test ===\n")
    
    for desc in test_descriptions:
        print(f"Description: \"{desc}\"")
        result = extract_features(desc)
        print(get_feature_summary(result))
        print()
