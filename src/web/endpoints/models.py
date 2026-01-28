"""
Pydantic models for API requests and responses.
"""
from typing import Optional
from pydantic import BaseModel


# ============================================================
# Common Models
# ============================================================

class GenerateResponse(BaseModel):
    project_id: str
    message: str


class FeedbackRequest(BaseModel):
    feedback: str
    rating: str  # "approved", "needs_work", "rejected"


# ============================================================
# New Project API Models (v2)
# ============================================================

class CreateProjectRequest(BaseModel):
    """Request to create a new project."""
    prompt: str
    template_id: Optional[str] = None
    name: Optional[str] = None


class CreateProjectResponse(BaseModel):
    """Response from creating a project."""
    project_id: str
    name: str
    template_source: Optional[str]
    message: str


class ConversationTurnRequest(BaseModel):
    """Request to add a conversation turn."""
    role: str  # "user", "assistant", "system"
    content: str
    metadata: Optional[dict] = None


class ConversationTurnResponse(BaseModel):
    """Response from adding a conversation turn."""
    role: str
    content: str
    timestamp: str


class BuildResponse(BaseModel):
    """Response from a build request."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    rom_path: Optional[str] = None


class TemplateInfo(BaseModel):
    """Template/sample information."""
    id: str
    name: str
    description: str
    complexity: int
    features: list[str]
    techniques: list[str]


class AgentConfigUpdate(BaseModel):
    """Request to update a single agent's configuration."""
    enabled: Optional[bool] = None
    model: Optional[str] = None


class SaveSpriteRequest(BaseModel):
    """Request to save a sprite."""
    name: str
    width: int
    height: int
    data: list[int]
    replace: Optional[str] = None  # Name of sprite to replace, if editing


class SchemaUpdateRequest(BaseModel):
    """Request to update the schema."""
    schema: dict


class DataRowRequest(BaseModel):
    """Request to create/update a data row."""
    row: dict


class UpdateTunableRequest(BaseModel):
    """Request to update a tunable parameter."""
    name: str
    value: int
    file: str


class UpdateTunablesRequest(BaseModel):
    """Request to update multiple tunables."""
    updates: list[UpdateTunableRequest]


class SnapshotInfo(BaseModel):
    """Info about a snapshot."""
    id: int
    timestamp: str
    description: str
    file_count: int


class CreateSnapshotRequest(BaseModel):
    """Request to create a snapshot."""
    description: str = ""


class RollbackRequest(BaseModel):
    """Request to rollback to a snapshot."""
    snapshot_id: int


class PipelineRequest(BaseModel):
    """Request to run the pipeline on a project."""
    message: str


class DialogueResponse(BaseModel):
    """Response from dialogue (chat without implementing)."""
    response: str
    conversation_length: int = 0


class BuildFeatureRequest(BaseModel):
    """Request to build features with optional explicit message."""
    message: Optional[str] = None  # If provided, added as feature_request before building


class BuildFeatureResponse(BaseModel):
    """Response from building features based on conversation."""
    success: bool
    response: str = ""
    features_implemented: list[str] = []
    files_changed: list[str] = []
    build_success: bool = True
    error: Optional[str] = None
    logs: list[dict] = []
    can_retry: bool = False  # True if retry_feature() can be called


class RetryFeatureRequest(BaseModel):
    """Request to retry a failed feature implementation."""
    additional_guidance: Optional[str] = None  # Extra instructions for the retry


class DevModeRequest(BaseModel):
    """Request for dev mode - direct implementation without Designer."""
    message: str  # The user's direct request
    attached_files: Optional[list[str]] = None  # Files to always include


class DevModeResponse(BaseModel):
    """Response from dev mode implementation."""
    success: bool
    response: str = ""  # Summary of what was done
    files_changed: list[str] = []
    build_success: bool = True
    error: Optional[str] = None
    logs: list[dict] = []
