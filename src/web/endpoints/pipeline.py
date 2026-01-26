"""
Pipeline (dialogue and build-feature) endpoints.
"""
import asyncio
import queue
import threading
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException

from project_api import get_api
from endpoints.models import (
    PipelineRequest, DialogueResponse, BuildFeatureRequest, BuildFeatureResponse,
    CreateProjectRequest, GenerateResponse, RetryFeatureRequest
)
from endpoints.websocket import manager
from endpoints.utils import active_tasks, pipeline_logs

router = APIRouter(prefix="/api/v2/projects/{project_id}", tags=["pipeline"])

# Separate router for endpoints that don't need project_id in path
generate_router = APIRouter(prefix="/api/v2", tags=["generate"])


@router.post("/new-chat")
async def new_chat(project_id: str):
    """
    Start a new chat by clearing conversation history.
    
    This clears the conversation.json for the project so the user
    can start fresh without stale context affecting the pipeline.
    """
    api = get_api()
    
    # Verify project exists
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Clear the conversation
    conversation = api.clear_conversation(project_id)
    
    # Broadcast to connected clients
    await manager.broadcast(project_id, {
        "type": "conversation_cleared",
        "conversation": conversation
    })
    
    return {"success": True, "conversation": conversation}


@router.post("/chat", response_model=DialogueResponse)
async def dialogue_chat(project_id: str, request: PipelineRequest):
    """
    Dialogue mode - chat with the Designer without implementing anything.
    
    This endpoint is for building up context and discussing features.
    When ready to implement, use POST /api/v2/projects/{project_id}/build-feature
    """
    from agents.pipeline import create_pipeline
    
    api = get_api()
    
    # Verify project exists
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Broadcast that we're starting dialogue
    await manager.broadcast(project_id, {
        "type": "dialogue_start",
        "message": request.message[:50] + "..."
    })
    
    try:
        pipeline = create_pipeline(verbose=True)
        response = pipeline.dialogue(project_id, request.message)
        
        # Get updated conversation length
        project = api.get_project(project_id)
        conv_length = len(project.conversation) if project.conversation else 0
        
        await manager.broadcast(project_id, {
            "type": "dialogue_complete",
            "response": response[:100] + "..."
        })
        
        return DialogueResponse(
            response=response,
            conversation_length=conv_length
        )
        
    except Exception as e:
        await manager.broadcast(project_id, {
            "type": "dialogue_error",
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/build-feature", response_model=BuildFeatureResponse)
async def build_feature(project_id: str, request: Optional[BuildFeatureRequest] = None):
    """
    Build features based on the conversation history.
    
    If a message is provided in the request, it's added to the conversation
    as a feature_request before building. This makes the typed message
    the explicit feature request for the pipeline.
    
    Uses project-specific agent configuration (models, enabled/disabled).
    Progress can be monitored via WebSocket at /ws/projects/{project_id}
    """
    from agents.pipeline import create_pipeline
    
    api = get_api()
    
    # Verify project exists
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # If a message was provided, add it as a feature_request turn
    if request and request.message:
        api.add_conversation_turn(
            project_id=project_id,
            role="user",
            content=request.message,
            metadata={"type": "feature_request"}
        )
        # Broadcast the message to connected clients
        await manager.broadcast(project_id, {
            "type": "chat_message",
            "role": "user",
            "content": request.message
        })
    
    # Get agent configuration for this project
    agent_config = api.get_agent_config(project_id)
    agents = agent_config["agents"]
    
    # Check if already processing
    if project_id in active_tasks:
        raise HTTPException(status_code=409, detail="Project is already being processed")
    
    # Initialize log storage for this project
    pipeline_logs[project_id] = []
    
    # Create a queue for log messages
    log_queue = queue.Queue()
    
    def log_callback(level: str, message: str):
        """Callback to capture pipeline logs."""
        log_entry = {"level": level, "message": message, "timestamp": datetime.now().isoformat()}
        pipeline_logs[project_id].append(log_entry)
        log_queue.put(log_entry)
    
    # Broadcast that we're starting
    await manager.broadcast(project_id, {
        "type": "build_feature_start",
        "message": "Building features from conversation..."
    })
    
    # Run pipeline in a thread so we can broadcast logs
    result_holder = {"result": None, "error": None}
    
    def run_build_thread():
        try:
            # Create pipeline with project-specific agent configuration
            pipeline = create_pipeline(
                designer_model=agents["designer"]["model"],
                coder_model=agents["coder"]["model"],
                reviewer_model=agents["reviewer"]["model"],
                cleanup_model=agents["cleanup"]["model"],
                verbose=True, 
                log_callback=log_callback,
                enable_reviewer=agents["reviewer"]["enabled"],
                enable_cleanup=agents["cleanup"]["enabled"]
            )
            result_holder["result"] = pipeline.build_from_conversation(project_id)
        except Exception as e:
            result_holder["error"] = str(e)
    
    # Start pipeline thread
    active_tasks[project_id] = True
    pipeline_thread = threading.Thread(target=run_build_thread)
    pipeline_thread.start()
    
    # Poll for logs and broadcast them while pipeline runs
    while pipeline_thread.is_alive():
        try:
            while not log_queue.empty():
                log_entry = log_queue.get_nowait()
                await manager.broadcast(project_id, {
                    "type": "pipeline_log",
                    "level": log_entry["level"],
                    "message": log_entry["message"]
                })
            await asyncio.sleep(0.1)
        except Exception:
            pass
    
    # Wait for thread to complete
    pipeline_thread.join()
    
    # Clean up active task
    if project_id in active_tasks:
        del active_tasks[project_id]
    
    # Send any remaining logs
    while not log_queue.empty():
        log_entry = log_queue.get_nowait()
        await manager.broadcast(project_id, {
            "type": "pipeline_log",
            "level": log_entry["level"],
            "message": log_entry["message"]
        })
    
    # Check for errors
    if result_holder["error"]:
        await manager.broadcast(project_id, {
            "type": "build_feature_error",
            "error": result_holder["error"]
        })
        raise HTTPException(status_code=500, detail=result_holder["error"])
    
    result = result_holder["result"]
    
    # Build response message
    if result.success and result.features_implemented:
        response = f"✅ Done! I implemented:\n\n"
        for f in result.features_implemented:
            response += f"- **{f}**\n"
        response += f"\nFiles changed: {', '.join(result.files_changed)}"
        if result.build_success:
            response += "\n\n🎮 Build successful - ready to play!"
        else:
            response += f"\n\n⚠️ Build had issues: {result.error}"
    elif result.success:
        response = "I analyzed the conversation but didn't identify any new features to implement. Could you be more specific about what you'd like to add?"
    else:
        response = f"❌ I encountered an error: {result.error}"
    
    # Broadcast completion
    await manager.broadcast(project_id, {
        "type": "build_feature_complete",
        "success": result.success,
        "features": result.features_implemented,
        "files": result.files_changed,
        "can_retry": result.can_retry
    })
    
    return BuildFeatureResponse(
        success=result.success,
        response=response,
        features_implemented=result.features_implemented,
        files_changed=result.files_changed,
        build_success=result.build_success,
        error=result.error,
        logs=pipeline_logs.get(project_id, []),
        can_retry=result.can_retry
    )


@router.post("/retry", response_model=BuildFeatureResponse)
async def retry_feature(project_id: str, request: RetryFeatureRequest = None):
    """
    Retry the last failed feature implementation.
    
    Uses saved context from the previous failed attempt.
    Optionally accepts additional guidance to help the retry succeed.
    """
    from agents.pipeline import create_pipeline
    
    api = get_api()
    
    # Verify project exists
    try:
        project = api.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Check if retry is in progress
    if project_id in active_tasks:
        raise HTTPException(
            status_code=409,
            detail="A task is already in progress for this project"
        )
    
    active_tasks[project_id] = "retry"
    pipeline_logs[project_id] = []
    
    # Set up logging
    log_queue = queue.Queue()
    
    def log_callback(level: str, message: str):
        log_queue.put({"level": level, "message": message, "timestamp": datetime.now().isoformat()})
        pipeline_logs[project_id].append({"level": level, "message": message})
    
    # Broadcast start
    await manager.broadcast(project_id, {
        "type": "retry_start"
    })
    
    # Create pipeline with logging
    pipeline = create_pipeline(log_callback=log_callback)
    
    # Run retry in background thread
    result_holder = {"result": None, "error": None}
    
    additional_guidance = request.additional_guidance if request else None
    
    def run_retry():
        try:
            result = pipeline.retry_feature(project_id, additional_guidance=additional_guidance)
            result_holder["result"] = result
        except Exception as e:
            result_holder["error"] = str(e)
    
    retry_thread = threading.Thread(target=run_retry)
    retry_thread.start()
    
    # Stream logs while running
    while retry_thread.is_alive():
        try:
            while not log_queue.empty():
                log_entry = log_queue.get_nowait()
                await manager.broadcast(project_id, {
                    "type": "pipeline_log",
                    "level": log_entry["level"],
                    "message": log_entry["message"]
                })
            await asyncio.sleep(0.1)
        except Exception:
            pass
    
    # Wait for thread to complete
    retry_thread.join()
    
    # Clean up active task
    if project_id in active_tasks:
        del active_tasks[project_id]
    
    # Send any remaining logs
    while not log_queue.empty():
        log_entry = log_queue.get_nowait()
        await manager.broadcast(project_id, {
            "type": "pipeline_log",
            "level": log_entry["level"],
            "message": log_entry["message"]
        })
    
    # Check for errors
    if result_holder["error"]:
        await manager.broadcast(project_id, {
            "type": "retry_error",
            "error": result_holder["error"]
        })
        raise HTTPException(status_code=500, detail=result_holder["error"])
    
    result = result_holder["result"]
    
    # Build response message
    if result.success and result.features_implemented:
        response = f"✅ Retry succeeded! I implemented:\n\n"
        for f in result.features_implemented:
            response += f"- **{f}**\n"
        response += f"\nFiles changed: {', '.join(result.files_changed)}"
        if result.build_success:
            response += "\n\n🎮 Build successful - ready to play!"
        else:
            response += f"\n\n⚠️ Build had issues: {result.error}"
    elif result.success:
        response = "Retry completed but no specific features were tracked."
    else:
        response = f"❌ Retry failed: {result.error}"
    
    # Broadcast completion
    await manager.broadcast(project_id, {
        "type": "retry_complete",
        "success": result.success,
        "features": result.features_implemented,
        "files": result.files_changed,
        "can_retry": result.can_retry
    })
    
    return BuildFeatureResponse(
        success=result.success,
        response=response,
        features_implemented=result.features_implemented,
        files_changed=result.files_changed,
        build_success=result.build_success,
        error=result.error,
        logs=pipeline_logs.get(project_id, []),
        can_retry=result.can_retry
    )


# ============================================================
# Generate Router - New Game Generation
# ============================================================

@generate_router.post("/generate", response_model=GenerateResponse)
async def generate_game(request: CreateProjectRequest):
    """
    Create a new project and start game generation.
    
    This replaces the legacy /api/generate endpoint.
    Creates a project with the initial prompt, then runs the pipeline
    to implement the game. Returns immediately with project_id.
    Connect to WebSocket for progress updates.
    """
    from agents.pipeline import create_pipeline
    
    api = get_api()
    
    # Create the project (this adds the prompt to conversation.json)
    project = api.create_project(
        prompt=request.prompt,
        template_id=request.template_id,
        name=request.name
    )
    project_id = project.id
    
    # Check if already processing
    if project_id in active_tasks:
        raise HTTPException(status_code=409, detail="Project is already being processed")
    
    # Initialize log storage for this project
    pipeline_logs[project_id] = []
    
    # Create a queue for log messages
    log_queue = queue.Queue()
    
    def log_callback(level: str, message: str):
        """Callback to capture pipeline logs."""
        log_entry = {"level": level, "message": message, "timestamp": datetime.now().isoformat()}
        pipeline_logs[project_id].append(log_entry)
        log_queue.put(log_entry)
    
    # Run pipeline in a background task
    async def run_generation():
        result_holder = {"result": None, "error": None}
        
        def run_build_thread():
            try:
                pipeline = create_pipeline(
                    verbose=True,
                    log_callback=log_callback
                )
                result_holder["result"] = pipeline.build_from_conversation(project_id)
            except Exception as e:
                result_holder["error"] = str(e)
        
        # Start pipeline thread
        active_tasks[project_id] = True
        pipeline_thread = threading.Thread(target=run_build_thread)
        pipeline_thread.start()
        
        # Broadcast that we're starting
        await manager.broadcast(project_id, {
            "type": "phase",
            "phase": "starting",
            "message": "Starting game generation..."
        })
        
        # Poll for logs and broadcast them while pipeline runs
        while pipeline_thread.is_alive():
            try:
                while not log_queue.empty():
                    log_entry = log_queue.get_nowait()
                    await manager.broadcast(project_id, {
                        "type": "pipeline_log",
                        "level": log_entry["level"],
                        "message": log_entry["message"]
                    })
                await asyncio.sleep(0.1)
            except Exception:
                pass
        
        # Wait for thread to complete
        pipeline_thread.join()
        
        # Clean up active task
        if project_id in active_tasks:
            del active_tasks[project_id]
        
        # Send any remaining logs
        while not log_queue.empty():
            log_entry = log_queue.get_nowait()
            await manager.broadcast(project_id, {
                "type": "pipeline_log",
                "level": log_entry["level"],
                "message": log_entry["message"]
            })
        
        # Check for errors
        if result_holder["error"]:
            await manager.broadcast(project_id, {
                "type": "complete",
                "success": False,
                "message": f"Generation failed: {result_holder['error']}"
            })
            return
        
        result = result_holder["result"]
        
        # Send completion
        if result.success and result.build_success:
            # Get ROM path from project
            updated_project = api.get_project(project_id)
            await manager.broadcast(project_id, {
                "type": "complete",
                "success": True,
                "message": "Game generated successfully!",
                "rom_path": updated_project.rom_path
            })
        elif result.success:
            await manager.broadcast(project_id, {
                "type": "complete",
                "success": False,
                "message": f"Build had issues: {result.error}"
            })
        else:
            await manager.broadcast(project_id, {
                "type": "complete",
                "success": False,
                "message": f"Generation failed: {result.error}"
            })
    
    # Start the background task
    asyncio.create_task(run_generation())
    
    return GenerateResponse(
        project_id=project_id,
        message="Generation started. Connect to WebSocket for progress."
    )
