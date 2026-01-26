"""
Pipeline Orchestrator v2 - Designer → Coder → Reviewer → Cleanup workflow.

This orchestrator:
1. Takes a project_id and user request
2. Runs Designer to analyze gaps and assemble context
3. Runs Coder to implement changes
4. Runs Reviewer to validate changes (blocks on critical issues)
5. Runs Cleanup to refactor for quality (optional)
6. Updates project summary
7. Records conversation history
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from ..designer import create_designer, DesignerAgent, ContextPackage
from ..coder.coder_agent import create_coder, CoderAgent, CoderResult
from ..reviewer import create_reviewer, CodeReviewer, ReviewResult
from ..cleanup import create_cleanup_agent, CleanupAgent, CleanupResult
from ..synthesis import create_synthesis_agent, SynthesisAgent
from ..project_api import get_api, ProjectAPI
from ..context.summary_generator import SummaryGenerator


@dataclass
class PipelineResult:
    """Result from running the pipeline."""
    success: bool
    project_id: str
    features_implemented: list[str]
    files_changed: list[str]
    build_success: bool
    review_passed: bool = True
    review_issues: list[dict] = None
    cleanup_applied: bool = False
    cleanup_changes: list[str] = None
    error: Optional[str] = None
    context_summary: Optional[str] = None
    # Retry support
    snapshot_id: Optional[str] = None  # For manual rollback
    can_retry: bool = False  # True if retry_feature() can be called
    last_reviewer_feedback: Optional[str] = None  # Feedback from last review failure


class PipelineV2:
    """
    Orchestrates the Designer → Coder → Reviewer → Cleanup workflow.
    
    This is the main entry point for the new workspace-based approach.
    """
    
    def __init__(
        self,
        designer_model: str = "claude-sonnet-4-20250514",
        coder_model: str = "claude-sonnet-4-20250514",
        reviewer_model: str = "claude-sonnet-4-20250514",
        cleanup_model: str = "claude-sonnet-4-20250514",
        verbose: bool = False,
        log_callback: callable = None,
        enable_reviewer: bool = True,
        enable_cleanup: bool = False
    ):
        """
        Initialize the pipeline.
        
        Args:
            designer_model: Model for gap analysis
            coder_model: Model for code generation
            reviewer_model: Model for code review
            cleanup_model: Model for code cleanup/refactoring
            verbose: Print debug info
            log_callback: Optional callback(level, message) for log messages
            enable_reviewer: Whether to run the reviewer (can be disabled for speed)
            enable_cleanup: Whether to run cleanup/refactoring after review
        """
        self.api = get_api()
        self.designer = create_designer(model=designer_model, verbose=verbose, log_callback=log_callback)
        self.coder = create_coder(model=coder_model, verbose=verbose, log_callback=log_callback)
        self.reviewer = create_reviewer(model=reviewer_model, verbose=verbose) if enable_reviewer else None
        self.cleanup = create_cleanup_agent(model=cleanup_model, verbose=verbose) if enable_cleanup else None
        self.synthesis = create_synthesis_agent(verbose=verbose)  # Uses Haiku by default
        self.enable_reviewer = enable_reviewer
        self.enable_cleanup = enable_cleanup
        self.verbose = verbose
        self.log_callback = log_callback
        
        # Retry state - stores context from last failed run
        self._last_context = None
        self._last_snapshot_id = None
        self._last_project_path = None
        self._last_reviewer_feedback = None
        
        # Log model configuration for cost tracking
        self._log("info", f"Pipeline models - Designer: {designer_model}, Coder: {coder_model}, Reviewer: {reviewer_model}, Synthesis: {self.synthesis.model}")
    
    def _get_retry_context_path(self, project_id: str) -> Path:
        """Get the path to the retry context file for a project."""
        project = self.api.get_project(project_id)
        return Path(project.path) / "context" / "retry_context.json"
    
    def _save_retry_context(self, project_id: str):
        """Save retry context to file for persistence across requests."""
        import json
        
        if not self._last_context:
            return
        
        retry_path = self._get_retry_context_path(project_id)
        retry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Serialize the context package
        context = self._last_context
        context_data = {
            "project_id": project_id,
            "snapshot_id": self._last_snapshot_id,
            "project_path": str(self._last_project_path) if self._last_project_path else None,
            "reviewer_feedback": self._last_reviewer_feedback,
            "timestamp": datetime.now().isoformat(),
            # ContextPackage fields
            "feature_gaps": [
                {"name": g.name, "description": g.description, "implementation_hints": g.implementation_hints}
                for g in (context.feature_gaps or [])
            ],
            "game_state_knowledge": context.game_state_knowledge,
            "file_context": context.file_context,
            "implementation_steps": context.implementation_steps,
            "constraints": context.constraints
        }
        
        with open(retry_path, "w") as f:
            json.dump(context_data, f, indent=2)
        
        self._log("info", f"💾 Saved retry context for {project_id[:8]}")
    
    def _load_retry_context(self, project_id: str) -> bool:
        """Load retry context from file. Returns True if loaded successfully."""
        import json
        
        retry_path = self._get_retry_context_path(project_id)
        
        if not retry_path.exists():
            return False
        
        try:
            with open(retry_path) as f:
                data = json.load(f)
            
            # Reconstruct ContextPackage  
            from ..designer import FeatureGap
            
            self._last_snapshot_id = data.get("snapshot_id")
            self._last_project_path = Path(data["project_path"]) if data.get("project_path") else None
            self._last_reviewer_feedback = data.get("reviewer_feedback")
            
            # Reconstruct feature gaps
            feature_gaps = [
                FeatureGap(
                    name=g["name"],
                    description=g["description"],
                    implementation_hints=g.get("implementation_hints", [])
                )
                for g in data.get("feature_gaps", [])
            ]
            
            # Create context package
            self._last_context = ContextPackage(
                feature_gaps=feature_gaps,
                game_state_knowledge=data.get("game_state_knowledge", ""),
                file_context=data.get("file_context", {}),
                implementation_steps=data.get("implementation_steps", []),
                constraints=data.get("constraints", [])
            )
            
            self._log("info", f"📂 Loaded retry context from {project_id[:8]}")
            return True
            
        except Exception as e:
            self._log("warning", f"Failed to load retry context: {e}")
            return False
    
    def _clear_retry_context(self, project_id: str):
        """Clear retry context file after successful completion."""
        retry_path = self._get_retry_context_path(project_id)
        if retry_path.exists():
            retry_path.unlink()
            self._log("info", "🗑️ Cleared retry context")
    
    def _log(self, level: str, message: str):
        """Log a message to console and callback."""
        if self.verbose:
            print(f"[Pipeline] {message}")
        if self.log_callback:
            try:
                self.log_callback(level, message)
            except Exception:
                pass  # Don't let callback errors break pipeline
    
    def run(
        self,
        project_id: str,
        user_request: str,
        skip_record: bool = False
    ) -> PipelineResult:
        """
        Run the full pipeline for a user request.
        
        Args:
            project_id: The project to modify
            user_request: What the user wants to do
            skip_record: If True, don't add to conversation (already recorded)
            
        Returns:
            PipelineResult with details of what happened
        """
        self._log("info", f"Starting pipeline for project {project_id[:8]}...")
        
        # Record user request in conversation (unless already recorded)
        if not skip_record:
            self.api.add_conversation_turn(
                project_id=project_id,
                role="user",
                content=user_request,
                metadata={"type": "feature_request"}
            )
        
        # Get project info
        project = self.api.get_project(project_id)
        project_path = project.path
        
        self._log("info", f"Project: {project.name}")
        self._log("info", f"Request: {user_request[:60]}...")
        
        # === PHASE 1: Designer ===
        self._log("agent", "🎨 Designer analyzing your request...")
        
        try:
            context = self.designer.assemble_context(project_id, user_request)
            
            self._log("info", f"Designer found {len(context.feature_gaps)} feature(s) to implement")
            for gap in context.feature_gaps:
                self._log("info", f"  • {gap.name}")
            
            if context.modifications:
                self._log("info", f"Designer found {len(context.modifications)} modification(s)")
                for mod in context.modifications:
                    self._log("info", f"  • {mod.feature}: {mod.change}")
        except Exception as e:
            self._log("error", f"Designer failed: {e}")
            return PipelineResult(
                success=False,
                project_id=project_id,
                features_implemented=[],
                files_changed=[],
                build_success=False,
                error=f"Designer failed: {e}"
            )
        
        # Check if there's actually work to do
        if not context.feature_gaps and not context.modifications and not context.schema_changes:
            self._log("info", "No feature gaps, modifications, or schema changes identified - nothing to implement")
            
            self.api.add_conversation_turn(
                project_id=project_id,
                role="assistant",
                content="I analyzed your request but didn't identify any changes to make. Could you be more specific about what you'd like?",
                metadata={"agent": "designer", "action": "no_work"}
            )
            
            return PipelineResult(
                success=True,
                project_id=project_id,
                features_implemented=[],
                files_changed=[],
                build_success=True,
                context_summary="No changes needed"
            )
        
        # Log schema changes if any
        if context.schema_changes:
            table_count = len(context.schema_changes.add_tables)
            field_count = len(context.schema_changes.add_fields)
            self._log("info", f"Designer identified {table_count} new table(s), {field_count} new field(s)")
        
        # === PHASE 1.5: Apply Schema Changes ===
        if context.schema_changes and (context.schema_changes.add_tables or context.schema_changes.add_fields):
            self._log("agent", "📊 Applying data schema changes...")
            
            try:
                self._apply_schema_changes(project_path, context.schema_changes)
                self._log("success", "Schema changes applied")
            except Exception as e:
                self._log("error", f"Schema changes failed: {e}")
                # Continue anyway - Coder can still work
        
        # === PHASE 2: Snapshot (for rollback) ===
        self._log("info", "💾 Creating backup snapshot...")
        snapshot_id = None
        
        try:
            feature_names = ", ".join(g.name for g in context.feature_gaps[:3])
            snapshot = self.api.create_snapshot(
                project_id,
                f"Before implementing: {feature_names}"
            )
            snapshot_id = snapshot['id']
            self._log("success", f"Snapshot #{snapshot_id} created")
        except Exception as e:
            self._log("warning", f"Snapshot failed: {e}")
        
        # === PHASE 3 & 4: Coder → Reviewer Loop ===
        # Retry up to MAX_REVIEW_RETRIES times if reviewer finds critical issues
        MAX_REVIEW_RETRIES = 2
        review_result = None
        coder_result = None
        reviewer_feedback = None
        
        # Store files before changes for diff generation
        before_files = self._read_project_files(project_path)
        
        # Store context for potential retry
        self._last_context = context
        self._last_snapshot_id = snapshot_id
        self._last_project_path = project_path
        self._last_reviewer_feedback = None
        
        for review_attempt in range(1, MAX_REVIEW_RETRIES + 1):
            attempt_label = f"(attempt {review_attempt}/{MAX_REVIEW_RETRIES})" if reviewer_feedback else ""
            
            # --- Coder Phase ---
            num_steps = len(context.implementation_steps) if hasattr(context, 'implementation_steps') else 0
            if num_steps > 0:
                self._log("agent", f"👨‍💻 Coder implementing {num_steps} steps... {attempt_label}")
            else:
                self._log("agent", f"👨‍💻 Coder implementing features... {attempt_label}")
            
            try:
                coder_result = self.coder.implement(
                    context, 
                    project_path,
                    reviewer_feedback=reviewer_feedback
                )
                
                if coder_result.success:
                    steps_msg = f" ({coder_result.steps_completed}/{coder_result.total_steps} steps)" if coder_result.total_steps > 0 else ""
                    self._log("success", f"Coder finished - {len(coder_result.files_changed)} files changed{steps_msg}")
                else:
                    self._log("error", f"Coder failed: {coder_result.error}")
                    # Store state for retry - NO auto-rollback
                    self._last_reviewer_feedback = reviewer_feedback
                    if snapshot_id:
                        self._log("info", f"💾 Snapshot available for rollback (ID: {snapshot_id})")
                        self._log("info", "Use rollback() to restore or retry_feature() to try again")
                    break  # Exit retry loop on coder failure
                    
            except Exception as e:
                self._log("error", f"Coder failed: {e}")
                # Store state for retry - NO auto-rollback
                self._last_reviewer_feedback = reviewer_feedback
                if snapshot_id:
                    self._log("info", f"💾 Snapshot available for rollback (ID: {snapshot_id})")
                self._save_retry_context(project_id)  # Persist for retry endpoint
                return PipelineResult(
                    success=False,
                    project_id=project_id,
                    features_implemented=[],
                    files_changed=[],
                    build_success=False,
                    error=f"Coder failed: {e}",
                    snapshot_id=snapshot_id,
                    can_retry=True
                )
            
            # --- Reviewer Phase (optional) ---
            if not (self.enable_reviewer and self.reviewer and coder_result.success):
                break  # Skip review, exit loop
            
            self._log("agent", f"🔍 Reviewer checking code changes... {attempt_label}")
            
            try:
                # Get files after changes
                after_files = self._read_project_files(project_path)
                
                # Calculate changed files for logging (reviewer already filters internally)
                changed_count = sum(
                    1 for path in set(before_files.keys()) | set(after_files.keys())
                    if before_files.get(path) != after_files.get(path)
                )
                total_files = len(set(before_files.keys()) | set(after_files.keys()))
                self._log("info", f"Reviewing {changed_count}/{total_files} changed files")
                
                # Build task description from feature gaps
                task_description = f"Implementing: {', '.join(g.name for g in context.feature_gaps)}\n"
                task_description += f"Request: {context.user_request}"
                
                # Run review on the diff
                review_result = self.reviewer.review_files(
                    task_description=task_description,
                    before_files=before_files,
                    after_files=after_files
                )
                
                if review_result.approved:
                    self._log("success", f"✅ Review passed ({review_result.warning_count} warnings)")
                    break  # Exit loop - review passed!
                else:
                    self._log("warning", f"⚠️ Review found {review_result.critical_count} critical issues")
                    
                    # Log the issues
                    for issue in review_result.issues:
                        level = "error" if issue.severity.value == "critical" else "warning"
                        self._log(level, f"  [{issue.severity.value}] {issue.file}: {issue.issue}")
                    
                    # Store feedback for potential manual retry
                    reviewer_feedback = review_result.feedback_for_coder()
                    self._last_reviewer_feedback = reviewer_feedback
                    
                    # Check if we should retry
                    if review_attempt < MAX_REVIEW_RETRIES:
                        self._log("info", f"🔄 Sending feedback to Coder for retry...")
                        # Don't break - continue loop to retry
                    else:
                        self._log("warning", f"⚠️ Max review retries reached")
                        self._log("info", f"💾 Snapshot available for rollback (ID: {snapshot_id})")
                        self._log("info", "Use rollback() to restore or retry_feature() to try again with the feedback")
                        # Return failure with retry info - NO auto-rollback
                        self._save_retry_context(project_id)  # Persist for retry endpoint
                        return PipelineResult(
                            success=False,
                            project_id=project_id,
                            features_implemented=coder_result.features_implemented if coder_result else [],
                            files_changed=[fc.path for fc in coder_result.files_changed] if coder_result else [],
                            build_success=coder_result.build_success if coder_result else False,
                            review_passed=False,
                            review_issues=[i.to_dict() for i in review_result.issues],
                            error=f"Review failed after {MAX_REVIEW_RETRIES} attempts",
                            snapshot_id=snapshot_id,
                            can_retry=True,
                            last_reviewer_feedback=reviewer_feedback
                        )
                    
            except Exception as e:
                self._log("warning", f"Review failed (continuing anyway): {e}")
                review_result = None
                break
        
        # === PHASE 5: Cleanup (optional) ===
        cleanup_result = None
        if self.enable_cleanup and self.cleanup and coder_result and coder_result.success:
            self._log("agent", "🧹 Cleanup agent refactoring code...")
            
            try:
                cleanup_result = self.cleanup.cleanup(
                    project_path=project_path,
                    recent_changes=coder_result.changes_made
                )
                
                if cleanup_result.success and cleanup_result.changes_made:
                    self._log("success", f"✨ Cleanup applied {len(cleanup_result.changes_made)} refactorings")
                    for change in cleanup_result.changes_made[:5]:
                        self._log("info", f"  • {change}")
                elif cleanup_result.success:
                    self._log("info", "Code is already clean - no refactoring needed")
                else:
                    self._log("warning", f"Cleanup failed: {cleanup_result.error}")
                    
            except Exception as e:
                self._log("warning", f"Cleanup failed (continuing anyway): {e}")
                cleanup_result = None
        
        # === PHASE 6: Update Project ===
        self._log("info", "🔄 Updating project state...")
        
        # If coder failed, rollback was already done in phase 3
        # Update status based on result
        if coder_result.success:
            self.api.update_status(project_id, "compiled")
        else:
            self.api.update_status(project_id, "build_failed", coder_result.error)
        
        # Regenerate summary
        self._log("info", "Updating project summary...")
        
        try:
            new_summary = self.api.update_summary(project_id)
        except Exception as e:
            self._log("warning", f"Summary regeneration failed: {e}")
        
        # Build status
        if coder_result.build_success:
            self._log("success", "🎮 Build successful!")
        else:
            self._log("error", f"⚠️ Build failed: {coder_result.error}")
        
        # Record result in conversation
        if coder_result.success:
            changes_str = "\n".join(f"- {c}" for c in coder_result.changes_made[:5])
            self.api.add_conversation_turn(
                project_id=project_id,
                role="assistant",
                content=f"✅ Done! I implemented:\n\n{changes_str}\n\nThe project builds successfully.",
                metadata={
                    "type": "build_feature_complete",  # Marker for conversation boundary
                    "agent": "coder",
                    "action": "implement",
                    "features": coder_result.features_implemented,
                    "files": [fc.path for fc in coder_result.files_changed]
                }
            )
            
            # === Update summary.features.added ===
            if coder_result.features_implemented:
                try:
                    project = self.api.get_project(project_id)
                    summary = project.summary
                    if summary and summary.features:
                        # Add new features (avoid duplicates)
                        existing = set(summary.features.added or [])
                        for feature in coder_result.features_implemented:
                            if feature not in existing:
                                summary.features.added.append(feature)
                        
                        # Save updated summary
                        generator = SummaryGenerator(str(project.path))
                        generator.save_summary(summary)
                        self._log("info", f"Updated summary with features: {coder_result.features_implemented}")
                except Exception as e:
                    self._log("warning", f"Failed to update summary features: {e}")
        else:
            self.api.add_conversation_turn(
                project_id=project_id,
                role="assistant",
                content=f"I tried to implement the features but encountered an error:\n\n{coder_result.error}",
                metadata={
                    "type": "build_feature_complete",  # Mark even failures as boundaries
                    "agent": "coder",
                    "action": "error",
                    "error": coder_result.error
                }
            )
        
        # Build review info for result
        review_passed = True
        review_issues = None
        if review_result:
            review_passed = review_result.approved
            review_issues = [i.to_dict() for i in review_result.issues] if review_result.issues else None
        
        # Build cleanup info for result
        cleanup_applied = False
        cleanup_changes = None
        if cleanup_result and cleanup_result.success and cleanup_result.changes_made:
            cleanup_applied = True
            cleanup_changes = cleanup_result.changes_made
        
        # Clear retry context on success
        if coder_result.success:
            self._clear_retry_context(project_id)
        
        return PipelineResult(
            success=coder_result.success,
            project_id=project_id,
            features_implemented=coder_result.features_implemented,
            files_changed=[fc.path for fc in coder_result.files_changed],
            build_success=coder_result.build_success,
            review_passed=review_passed,
            review_issues=review_issues,
            cleanup_applied=cleanup_applied,
            cleanup_changes=cleanup_changes,
            error=coder_result.error,
            context_summary=f"Implemented {len(coder_result.features_implemented)} features"
        )
    
    def _read_project_files(self, project_path: Path) -> dict[str, str]:
        """Read all source files from project for diff generation."""
        files = {}
        src_path = project_path / "src"
        
        if src_path.exists():
            for ext in ["*.c", "*.h"]:
                for f in src_path.glob(ext):
                    rel_path = f"src/{f.name}"
                    try:
                        files[rel_path] = f.read_text()
                    except Exception:
                        pass  # Skip unreadable files
        
        return files
    
    def _apply_schema_changes(self, project_path: Path, schema_changes) -> None:
        """
        Apply data schema changes to the project.
        
        Updates _schema.json and creates initial data files as needed.
        """
        import json
        
        schema_path = project_path / "_schema.json"
        data_dir = project_path / "data"
        
        # Load or create schema
        if schema_path.exists():
            with open(schema_path) as f:
                schema = json.load(f)
        else:
            schema = {"version": 1, "tables": {}}
        
        # Add new tables
        for table_def in schema_changes.add_tables:
            table_name = table_def.get("name")
            if table_name:
                schema["tables"][table_name] = {
                    "description": table_def.get("description", ""),
                    "fields": table_def.get("fields", {})
                }
                
                # Create empty data file if it doesn't exist
                data_dir.mkdir(exist_ok=True)
                data_file = data_dir / f"{table_name}.json"
                if not data_file.exists():
                    with open(data_file, "w") as f:
                        json.dump([], f)
        
        # Add new fields to existing tables
        for field_add in schema_changes.add_fields:
            table_name = field_add.get("table")
            field_name = field_add.get("name")
            field_def = field_add.get("field", {})
            
            if table_name in schema["tables"]:
                schema["tables"][table_name]["fields"][field_name] = field_def
        
        # Remove tables
        for table_name in schema_changes.remove_tables:
            if table_name in schema["tables"]:
                del schema["tables"][table_name]
        
        # Remove fields
        for field_rem in schema_changes.remove_fields:
            table_name = field_rem.get("table")
            field_name = field_rem.get("name")
            if table_name in schema["tables"]:
                fields = schema["tables"][table_name].get("fields", {})
                if field_name in fields:
                    del fields[field_name]
        
        # Write updated schema
        with open(schema_path, "w") as f:
            json.dump(schema, f, indent=2)
    
    def rollback(self, project_id: str, snapshot_id: str = None) -> bool:
        """
        Explicitly rollback to a previous snapshot.
        
        Args:
            project_id: The project to rollback
            snapshot_id: Specific snapshot ID, or None to use last stored snapshot
            
        Returns:
            True if rollback successful
        """
        target_snapshot = snapshot_id or self._last_snapshot_id
        
        if not target_snapshot:
            self._log("error", "No snapshot available for rollback")
            return False
        
        self._log("info", f"⏪ Rolling back to snapshot {target_snapshot}...")
        
        try:
            self.api.rollback_to_snapshot(project_id, target_snapshot)
            self._log("success", "Rolled back successfully")
            
            # Clear retry state after rollback
            self._last_context = None
            self._last_snapshot_id = None
            self._last_project_path = None
            self._last_reviewer_feedback = None
            
            return True
        except Exception as e:
            self._log("error", f"Rollback failed: {e}")
            return False
    
    def retry_feature(self, project_id: str, additional_guidance: str = None) -> PipelineResult:
        """
        Retry the last failed feature implementation.
        
        Picks up from where the Coder left off, using stored context and
        any reviewer feedback from the previous attempt.
        
        Args:
            project_id: The project to retry
            additional_guidance: Optional extra instructions for the retry
            
        Returns:
            PipelineResult from the retry attempt
        """
        # Try to load context from file if not in memory
        if not self._last_context:
            if not self._load_retry_context(project_id):
                self._log("error", "No previous context available for retry")
                return PipelineResult(
                    success=False,
                    project_id=project_id,
                    features_implemented=[],
                    files_changed=[],
                    build_success=False,
                    error="No previous context available. Run a feature request first."
                )
        
        self._log("info", "🔄 Retrying feature implementation...")
        
        context = self._last_context
        project_path = self._last_project_path
        reviewer_feedback = self._last_reviewer_feedback
        
        # Add any additional guidance to the feedback
        if additional_guidance:
            if reviewer_feedback:
                reviewer_feedback += f"\n\n## Additional Guidance\n{additional_guidance}"
            else:
                reviewer_feedback = f"## Additional Guidance\n{additional_guidance}"
            self._log("info", f"Added guidance: {additional_guidance[:50]}...")
        
        # Run the Coder with the stored context and feedback
        self._log("agent", "👨‍💻 Coder retrying implementation...")
        
        try:
            coder_result = self.coder.implement(
                context,
                project_path,
                reviewer_feedback=reviewer_feedback
            )
            
            if coder_result.success:
                self._log("success", f"Coder finished - {len(coder_result.files_changed)} files changed")
                
                # Clear retry state on success
                self._last_context = None
                self._last_reviewer_feedback = None
                self._clear_retry_context(project_id)  # Clear persisted context
                
                # Run reviewer if enabled
                if self.enable_reviewer and self.reviewer:
                    self._log("agent", "🔍 Reviewer checking retry changes...")
                    
                    before_files = self._read_project_files(project_path)
                    after_files = self._read_project_files(project_path)
                    
                    task_description = f"Retry implementing: {', '.join(g.name for g in context.feature_gaps)}"
                    review_result = self.reviewer.review_files(
                        task_description=task_description,
                        before_files=before_files,
                        after_files=after_files
                    )
                    
                    if review_result.approved:
                        self._log("success", f"✅ Review passed ({review_result.warning_count} warnings)")
                    else:
                        self._log("warning", f"⚠️ Review found {review_result.critical_count} critical issues")
                        self._last_reviewer_feedback = review_result.feedback_for_coder()
                        self._last_context = context  # Keep for another retry
                        self._save_retry_context(project_id)  # Persist for retry endpoint
                        
                        return PipelineResult(
                            success=False,
                            project_id=project_id,
                            features_implemented=coder_result.features_implemented,
                            files_changed=[fc.path for fc in coder_result.files_changed],
                            build_success=coder_result.build_success,
                            review_passed=False,
                            review_issues=[i.to_dict() for i in review_result.issues],
                            error="Review failed - retry available",
                            snapshot_id=self._last_snapshot_id,
                            can_retry=True,
                            last_reviewer_feedback=self._last_reviewer_feedback
                        )
                
                return PipelineResult(
                    success=True,
                    project_id=project_id,
                    features_implemented=coder_result.features_implemented,
                    files_changed=[fc.path for fc in coder_result.files_changed],
                    build_success=coder_result.build_success,
                    review_passed=True
                )
            else:
                self._log("error", f"Coder retry failed: {coder_result.error}")
                return PipelineResult(
                    success=False,
                    project_id=project_id,
                    features_implemented=[],
                    files_changed=[],
                    build_success=False,
                    error=f"Coder retry failed: {coder_result.error}",
                    snapshot_id=self._last_snapshot_id,
                    can_retry=True
                )
                
        except Exception as e:
            self._log("error", f"Retry failed: {e}")
            return PipelineResult(
                success=False,
                project_id=project_id,
                features_implemented=[],
                files_changed=[],
                build_success=False,
                error=f"Retry failed: {e}",
                snapshot_id=self._last_snapshot_id,
                can_retry=True
            )
    
    def dialogue(self, project_id: str, message: str) -> str:
        """
        Pure dialogue mode - just chat without implementing anything.
        
        Uses the Designer's knowledge of the project to have a conversation,
        answer questions, and build up context for future feature requests.
        
        Args:
            project_id: The project to discuss
            message: User's message
            
        Returns:
            Assistant's response text
        """
        import anthropic
        
        # Get project context
        project = self.api.get_project(project_id)
        summary = project.summary
        
        # Get conversation history for context
        conversation = project.conversation[-10:] if project.conversation else []  # Last 10 turns
        
        # Build context about the project
        project_context = f"""You are a helpful GameBoy game designer assistant. You're working on a project called "{project.name}".

Current project status: {project.status}
Template: {project.template_source or 'blank'}

"""
        if summary:
            # Get all features from FeatureSet
            all_features = []
            if summary.features:
                all_features = (summary.features.from_template or []) + (summary.features.added or [])
            
            project_context += f"""Project Summary:
- Files: {', '.join(f.path for f in summary.files) if summary.files else 'none yet'}
- Features: {', '.join(all_features) if all_features else 'none yet'}
- Patterns: {', '.join(summary.patterns) if summary.patterns else 'basic'}
- Known Issues: {', '.join(str(i) for i in summary.known_issues) if summary.known_issues else 'none'}
"""
        
        system = f"""{project_context}
You are having a conversation with the user about their GameBoy game project.
Your role is to:
1. Discuss ideas and features they want to add
2. Ask clarifying questions to understand their vision
3. Suggest GameBoy-appropriate implementations
4. Help them think through game mechanics
5. Build context that will help when they're ready to implement

This is DIALOGUE mode - you are NOT implementing anything right now.
When the user is ready to actually build features, they will click "Build Feature" 
which will use the conversation history to create a design plan.

Keep responses conversational but focused on game development.
Use **bold** for emphasis. Be encouraging and creative."""

        # Build messages array with conversation history
        messages = []
        for turn in conversation:
            if turn.role in ('user', 'assistant'):
                messages.append({"role": turn.role, "content": turn.content})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call Claude
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=self.designer.model,
            max_tokens=800,
            system=system,
            messages=messages
        )
        
        response_text = response.content[0].text
        
        # Record in conversation
        self.api.add_conversation_turn(
            project_id=project_id,
            role="user",
            content=message,
            metadata={"type": "dialogue"}
        )
        self.api.add_conversation_turn(
            project_id=project_id,
            role="assistant",
            content=response_text,
            metadata={"agent": "designer", "action": "dialogue"}
        )
        
        self._log("info", "Dialogue turn completed")
        
        return response_text
    
    def build_from_conversation(self, project_id: str) -> PipelineResult:
        """
        Build features based on the conversation history.
        
        This reads the conversation, has the Designer synthesize it into
        a feature request, then runs the implementation pipeline.
        
        Only uses conversation turns AFTER the last completed feature build
        to avoid re-implementing old features.
        
        Args:
            project_id: The project to build
            
        Returns:
            PipelineResult with implementation details
        """
        self._log("info", f"Building features from conversation for {project_id[:8]}...")
        
        # Get project and conversation
        project = self.api.get_project(project_id)
        conversation = project.conversation
        
        if not conversation:
            return PipelineResult(
                success=False,
                project_id=project_id,
                features_implemented=[],
                files_changed=[],
                build_success=False,
                error="No conversation history to build from"
            )
        
        # Find the last feature build completion marker
        # Only process conversation AFTER this point to avoid re-building old features
        last_build_idx = -1
        for i, turn in enumerate(conversation):
            metadata = turn.metadata or {}
            # Look for build completion markers
            if (metadata.get('type') == 'build_feature_complete' or
                metadata.get('type') == 'build_complete' or
                (turn.role == 'assistant' and '✅ Done! I implemented:' in turn.content)):
                last_build_idx = i
        
        # Only use conversation after the last build completion
        if last_build_idx >= 0:
            self._log("info", f"Found previous build at turn {last_build_idx + 1}, using conversation from turn {last_build_idx + 2}")
            conversation = conversation[last_build_idx + 1:]
        
        # Get all user/assistant messages since last build (including feature_request types)
        # This bundles all context for the current feature together
        dialogue_turns = [
            t for t in conversation 
            if t.role in ('user', 'assistant')
        ]
        
        if not dialogue_turns:
            return PipelineResult(
                success=False,
                project_id=project_id,
                features_implemented=[],
                files_changed=[],
                build_success=False,
                error="No new features discussed since last build. Start a new conversation about what you'd like to add!"
            )
        
        # Synthesize conversation into a feature request using the lightweight synthesis agent
        self._log("agent", "🎨 Synthesis agent converting conversation to feature plan...")
        
        synthesis_result = self.synthesis.synthesize_from_turns(
            turns=dialogue_turns,
            project_context=f"Project: {project.name}"
        )
        
        if not synthesis_result.success:
            return PipelineResult(
                success=False,
                project_id=project_id,
                features_implemented=[],
                files_changed=[],
                build_success=False,
                error=f"Failed to synthesize conversation: {synthesis_result.error}"
            )
        
        synthesized_request = synthesis_result.synthesized_request
        self._log("info", f"Synthesized request: {synthesized_request[:80]}...")
        
        # Now run the normal pipeline with the synthesized request
        # skip_record=True because the feature request is already in the conversation
        return self.run(project_id, synthesized_request, skip_record=True)
    
    def chat(
        self,
        project_id: str,
        message: str
    ) -> str:
        """
        Simple dialogue interface (returns just string).
        Now only does dialogue, no implementation.
        """
        return self.dialogue(project_id, message)


def create_pipeline(
    designer_model: str = "claude-sonnet-4-20250514",
    coder_model: str = "claude-sonnet-4-20250514",
    reviewer_model: str = "claude-sonnet-4-20250514",
    cleanup_model: str = "claude-sonnet-4-20250514",
    verbose: bool = False,
    log_callback: callable = None,
    enable_reviewer: bool = True,
    enable_cleanup: bool = False
) -> PipelineV2:
    """Factory function to create a pipeline."""
    return PipelineV2(
        designer_model=designer_model,
        coder_model=coder_model,
        reviewer_model=reviewer_model,
        cleanup_model=cleanup_model,
        verbose=verbose,
        log_callback=log_callback,
        enable_reviewer=enable_reviewer,
        enable_cleanup=enable_cleanup
    )
