"""
Corpus search utilities for the planning agent.

Provides functions to query the manifest and retrieve relevant code samples
based on feature requirements.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Set, Optional

# Path to the corpus
CORPUS_ROOT = Path(__file__).parent.parent.parent.parent / "games"
MANIFEST_PATH = CORPUS_ROOT / "manifest.json"


def load_manifest() -> Dict:
    """Load the corpus manifest."""
    with open(MANIFEST_PATH, "r") as f:
        return json.load(f)


def get_all_features() -> Set[str]:
    """Get all available features from the taxonomy."""
    manifest = load_manifest()
    features = set()
    for category in manifest["taxonomy"]["categories"].values():
        features.update(category["subcategories"])
    return features


def search_by_features(features: List[str]) -> List[Dict]:
    """
    Find samples that demonstrate the given features.
    
    Args:
        features: List of feature names (e.g., ["gravity", "sprites", "collision_aabb"])
    
    Returns:
        List of sample metadata dicts, ranked by relevance (most matching features first)
    """
    manifest = load_manifest()
    feature_index = manifest["feature_index"]
    samples_by_id = {s["id"]: s for s in manifest["samples"]}
    
    # Count how many requested features each sample covers
    sample_scores = {}
    for feature in features:
        if feature in feature_index:
            for sample_id in feature_index[feature]:
                sample_scores[sample_id] = sample_scores.get(sample_id, 0) + 1
    
    # Sort by score (most relevant first)
    ranked_ids = sorted(sample_scores.keys(), key=lambda x: sample_scores[x], reverse=True)
    
    # Return full sample metadata
    results = []
    for sample_id in ranked_ids:
        sample = samples_by_id[sample_id].copy()
        sample["relevance_score"] = sample_scores[sample_id]
        sample["matched_features"] = [f for f in features if sample_id in feature_index.get(f, [])]
        results.append(sample)
    
    return results


def get_sample_files(sample_id: str) -> Dict[str, str]:
    """
    Get all source files for a sample.
    
    Args:
        sample_id: The sample identifier (e.g., "pong", "runner")
    
    Returns:
        Dict mapping relative paths to absolute paths
    """
    sample_path = CORPUS_ROOT / "samples" / sample_id / "src"
    files = {}
    
    if sample_path.exists():
        for f in sample_path.glob("*.c"):
            files[f"src/{f.name}"] = str(f)
        for f in sample_path.glob("*.h"):
            files[f"src/{f.name}"] = str(f)
    
    return files


def read_sample_file(sample_id: str, relative_path: str) -> Optional[str]:
    """
    Read a specific file from a sample.
    
    Args:
        sample_id: The sample identifier
        relative_path: Path relative to sample root (e.g., "src/game.c")
    
    Returns:
        File contents as string, or None if not found
    """
    file_path = CORPUS_ROOT / "samples" / sample_id / relative_path
    if file_path.exists():
        with open(file_path, "r") as f:
            return f.read()
    return None


def extract_function(content: str, function_name: str) -> Optional[str]:
    """
    Extract a specific function from C source code.
    
    Simple extraction - finds function by name and extracts until matching brace.
    
    Args:
        content: C source code
        function_name: Name of function to extract
    
    Returns:
        Function code including signature and body, or None if not found
    """
    import re
    
    # Pattern to find function definition
    # Matches: return_type function_name(params) {
    pattern = rf'(\w+[\s\*]+{function_name}\s*\([^)]*\)\s*\{{)'
    match = re.search(pattern, content)
    
    if not match:
        return None
    
    start = match.start()
    
    # Find matching closing brace
    brace_count = 0
    in_function = False
    end = start
    
    for i, char in enumerate(content[start:], start):
        if char == '{':
            brace_count += 1
            in_function = True
        elif char == '}':
            brace_count -= 1
            if in_function and brace_count == 0:
                end = i + 1
                break
    
    return content[start:end]


def get_feature_examples(feature: str) -> List[Dict]:
    """
    Get code examples for a specific feature.
    
    Args:
        feature: Feature name (e.g., "gravity", "scrolling")
    
    Returns:
        List of dicts with sample_id, file, and relevant code snippets
    """
    manifest = load_manifest()
    feature_index = manifest["feature_index"]
    
    if feature not in feature_index:
        return []
    
    examples = []
    
    # Feature to likely function mapping
    feature_functions = {
        "gravity": ["game_update"],
        "scrolling": ["game_update", "game_setup_background"],
        "collision_aabb": ["check_collision", "game_update"],
        "collision_tile": ["check_collision", "check_brick_collision"],
        "sprites": ["sprites_init", "game_render"],
        "animation": ["game_update", "game_render"],
        "music": ["sound_play_note", "sound_init"],
        "save_sram": ["save_load", "save_write"],
        "rng": ["random", "game_update"],
        "ai": ["game_update"],
        "velocity": ["game_update"],
        "bounce": ["game_update"],
    }
    
    relevant_functions = feature_functions.get(feature, ["game_update", "game_init"])
    
    for sample_id in feature_index[feature]:
        game_c = read_sample_file(sample_id, "src/game.c")
        if game_c:
            for func_name in relevant_functions:
                func_code = extract_function(game_c, func_name)
                if func_code:
                    examples.append({
                        "sample_id": sample_id,
                        "file": "src/game.c",
                        "function": func_name,
                        "code": func_code
                    })
                    break  # One example per sample
    
    return examples


def get_missing_features() -> List[str]:
    """Get list of features not yet covered by any sample."""
    manifest = load_manifest()
    return manifest.get("missing_coverage", [])


if __name__ == "__main__":
    # Test the corpus search
    print("=== Corpus Search Test ===\n")
    
    print("All features:")
    print(sorted(get_all_features()))
    print()
    
    print("Searching for: gravity, sprites, collision_aabb")
    results = search_by_features(["gravity", "sprites", "collision_aabb"])
    for r in results:
        print(f"  {r['id']}: score={r['relevance_score']}, matched={r['matched_features']}")
    print()
    
    print("Gravity examples:")
    examples = get_feature_examples("gravity")
    for ex in examples[:2]:
        print(f"  {ex['sample_id']}/{ex['file']} - {ex['function']}()")
        print(f"    {ex['code'][:100]}...")
