#!/usr/bin/env python3
"""
Migration script to add context/ folders to existing projects.

This script:
1. Finds all projects in games/projects/
2. Generates a summary.json for each project
3. Creates the context/ folder structure

Usage:
    python -m src.agents.context.migrate [--dry-run]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.context.summary_generator import SummaryGenerator, generate_summary


def find_projects(base_path: Path) -> list[Path]:
    """Find all project directories."""
    projects = []
    
    for item in base_path.iterdir():
        if item.is_dir() and (item / "metadata.json").exists():
            projects.append(item)
    
    return sorted(projects)


def find_samples(base_path: Path) -> list[Path]:
    """Find all sample directories."""
    samples = []
    
    for item in base_path.iterdir():
        if item.is_dir() and (item / "metadata.json").exists():
            samples.append(item)
    
    return sorted(samples)


def load_sample_metadata(samples_path: Path) -> dict[str, dict]:
    """Load metadata for all samples, indexed by name."""
    samples = {}
    
    for sample_dir in find_samples(samples_path):
        metadata_path = sample_dir / "metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
            samples[metadata.get('name', sample_dir.name)] = metadata
    
    return samples


def migrate_project(
    project_path: Path, 
    sample_metadata: dict[str, dict],
    dry_run: bool = False
) -> dict:
    """Migrate a single project to have context/ folder."""
    result = {
        "project": project_path.name,
        "status": "unknown",
        "message": ""
    }
    
    try:
        # Check if already migrated
        context_dir = project_path / "context"
        summary_path = context_dir / "summary.json"
        
        if summary_path.exists():
            result["status"] = "skipped"
            result["message"] = "Already has context/summary.json"
            return result
        
        # Load project plan to find template
        plan_path = project_path / "plan.json"
        template_metadata = None
        
        if plan_path.exists():
            plan = json.loads(plan_path.read_text())
            template_name = plan.get('template_sample')
            if template_name and template_name in sample_metadata:
                template_metadata = sample_metadata[template_name]
        
        # Generate summary
        generator = SummaryGenerator(str(project_path))
        summary = generator.generate(template_metadata)
        
        if dry_run:
            result["status"] = "dry_run"
            result["message"] = f"Would create context/summary.json ({len(summary.files)} files parsed)"
            result["preview"] = {
                "project_name": summary.project_name,
                "current_state": summary.current_state,
                "files": [f.path for f in summary.files],
                "patterns": summary.patterns,
                "known_issues": len(summary.known_issues)
            }
        else:
            # Create context directory and save
            context_dir.mkdir(exist_ok=True)
            
            # Also create empty conversation.json
            conversation_path = context_dir / "conversation.json"
            conversation_path.write_text(json.dumps({
                "project_id": summary.project_id,
                "turns": [],
                "created_at": datetime.now().isoformat()
            }, indent=2))
            
            # Save summary
            output_path = generator.save_summary(summary)
            
            result["status"] = "migrated"
            result["message"] = f"Created {output_path}"
            result["summary"] = {
                "files_parsed": len(summary.files),
                "patterns_detected": summary.patterns,
                "known_issues": len(summary.known_issues)
            }
    
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
    
    return result


def migrate_sample(
    sample_path: Path,
    dry_run: bool = False
) -> dict:
    """Migrate a sample project (has slightly different metadata structure)."""
    result = {
        "sample": sample_path.name,
        "status": "unknown", 
        "message": ""
    }
    
    try:
        context_dir = sample_path / "context"
        summary_path = context_dir / "summary.json"
        
        if summary_path.exists():
            result["status"] = "skipped"
            result["message"] = "Already has context/summary.json"
            return result
        
        # For samples, they ARE the template
        generator = SummaryGenerator(str(sample_path))
        
        # Custom generate for samples (different metadata structure)
        metadata = json.loads((sample_path / "metadata.json").read_text())
        files = generator._parse_source_files()
        patterns = generator._detect_patterns(files)
        
        from src.agents.context.schemas import ProjectSummary, FeatureSet
        
        summary = ProjectSummary(
            project_id=f"sample-{metadata.get('name', sample_path.name)}",
            project_name=metadata.get('name', sample_path.name),
            description=metadata.get('description', ''),
            template_source=None,  # Samples are the template
            template_name=None,
            current_state='refined',  # Samples are complete
            features=FeatureSet(
                from_template=[],
                added=metadata.get('features', []),
                planned=[]
            ),
            files=files,
            patterns=patterns,
            known_issues=[],
            last_build_success=True,
            last_build_error=None,
            rom_size_bytes=metadata.get('rom_size_kb', 32) * 1024,
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            summary_generated_at=datetime.now().isoformat()
        )
        
        if dry_run:
            result["status"] = "dry_run"
            result["message"] = f"Would create context/summary.json ({len(summary.files)} files)"
            result["preview"] = {
                "name": summary.project_name,
                "features": summary.features.added,
                "patterns": summary.patterns
            }
        else:
            context_dir.mkdir(exist_ok=True)
            generator.save_summary(summary, str(summary_path))
            
            result["status"] = "migrated"
            result["message"] = f"Created {summary_path}"
    
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Migrate projects to use context/ folders")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    parser.add_argument("--projects-only", action="store_true", help="Only migrate projects, not samples")
    parser.add_argument("--samples-only", action="store_true", help="Only migrate samples, not projects")
    args = parser.parse_args()
    
    # Find base paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent
    
    projects_path = project_root / "games" / "projects"
    samples_path = project_root / "games" / "samples"
    
    print("=" * 60)
    print("Project Context Migration")
    print("=" * 60)
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be written\n")
    
    results = {"projects": [], "samples": []}
    
    # Migrate projects
    if not args.samples_only:
        print("\n📁 Migrating Projects...")
        print("-" * 40)
        
        sample_metadata = load_sample_metadata(samples_path)
        projects = find_projects(projects_path)
        
        for project_path in projects:
            result = migrate_project(project_path, sample_metadata, args.dry_run)
            results["projects"].append(result)
            
            status_icon = {
                "migrated": "✅",
                "skipped": "⏭️",
                "dry_run": "🔍",
                "error": "❌"
            }.get(result["status"], "❓")
            
            print(f"  {status_icon} {result['project']}: {result['message']}")
    
    # Migrate samples
    if not args.projects_only:
        print("\n📁 Migrating Samples...")
        print("-" * 40)
        
        samples = find_samples(samples_path)
        
        for sample_path in samples:
            result = migrate_sample(sample_path, args.dry_run)
            results["samples"].append(result)
            
            status_icon = {
                "migrated": "✅",
                "skipped": "⏭️",
                "dry_run": "🔍",
                "error": "❌"
            }.get(result["status"], "❓")
            
            print(f"  {status_icon} {result['sample']}: {result['message']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for category in ["projects", "samples"]:
        if results[category]:
            total = len(results[category])
            migrated = sum(1 for r in results[category] if r["status"] in ("migrated", "dry_run"))
            skipped = sum(1 for r in results[category] if r["status"] == "skipped")
            errors = sum(1 for r in results[category] if r["status"] == "error")
            
            print(f"\n{category.capitalize()}: {total} total")
            print(f"  - {'Would migrate' if args.dry_run else 'Migrated'}: {migrated}")
            print(f"  - Skipped (existing): {skipped}")
            if errors:
                print(f"  - Errors: {errors}")


if __name__ == "__main__":
    main()
