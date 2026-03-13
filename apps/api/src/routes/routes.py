from __future__ import annotations
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse
import io
from src.clients.core_api import CoreAPIClient
from src.clients.doc_processing_api import DocumentProcessingAPIClient
from src.core.audit import AuditTrail
from src.core.config import settings
from src.core.security import Principal, get_principal
from src.orchestrator.graph import Orchestrator
from src.orchestrator.state import GraphState
from src.schemas.requests import ChatRequest
from src.schemas.responses import ChatResponse
from src.schemas.common import AuditBundle
from src.services.history import SessionHistoryService
from src.services.metrics import Metrics
from src.agents.mercer_workbook_ingestion import MercerWorkbookIngestionAgent
from src.routes import jobs, projects, match_result


router = APIRouter()

# Include sub-routers
router.include_router(projects.router)
router.include_router(jobs.router)
router.include_router(match_result.router)


def _core() -> CoreAPIClient:
    return CoreAPIClient()


def _doc() -> DocumentProcessingAPIClient:
    return DocumentProcessingAPIClient()


@router.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@router.get("/metrics")
async def metrics():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
    # return JSONResponse(
    # content=generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST
    # )


@router.post("/ingest-mercer-workbook")
async def ingest_mercer_workbook(
    principal: Principal = Depends(get_principal),
    core_api: CoreAPIClient = Depends(_core),
):
    """Ingest Mercer IPE Workbook into MongoDB vector store.

    Requires admin/service account permissions.
    """
    audit = AuditTrail()
    audit.add("ingest_start", {"subject": principal.subject})

    try:
        agent = MercerWorkbookIngestionAgent(core_api)
        result = await agent.run({}, audit)

        audit.add("ingest_end", {"status": result.output.get("status")})

        return {
            "status": "success",
            "message": "Mercer Workbook ingestion completed",
            "details": result.output,
            "audit": audit.export() if settings.enable_audit_trail else None,
        }

    except Exception as e:
        audit.add("ingest_error", {"error": str(e)})
        return {
            "status": "error",
            "message": str(e),
            "audit": audit.export() if settings.enable_audit_trail else None,
        }


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    principal: Principal = Depends(get_principal),
    core_api: CoreAPIClient = Depends(_core),
):
    m = Metrics("chat")
    audit = AuditTrail()
    audit.add(
        "request_start",
        {"route": "/chat", "subject": principal.subject, "session_id": req.session_id},
    )

    # Extract project_id and job_ids from user_context
    project_id = req.user_context.get("project_id")
    job_ids = req.user_context.get("job_ids", [])

    # Ensure job_ids is a list
    if isinstance(job_ids, str):
        job_ids = [job_ids]
    elif not isinstance(job_ids, list):
        job_ids = []

    audit.add(
        "context_extracted",
        {
            "project_id": project_id,
            "job_ids": job_ids,
            "has_context": bool(project_id or job_ids),
        },
    )

    import logging

    logger = logging.getLogger("chat-endpoint-debug")
    history = SessionHistoryService(core_api)
    logger.info("Before await history.append user")
    await history.append(req.session_id, "user", req.user_query)
    logger.info("After await history.append user")

    orch = Orchestrator(core_api)
    state = GraphState(
        session_id=req.session_id,
        user_query=req.user_query,
        task=req.task or "auto",
        project_id=project_id,
        job_ids=job_ids,
    )

    logger.info("Before await orch.run")
    out_state = await orch.run(state, audit)
    logger.info("After await orch.run")

    final_answer = "See fused output for details."
    fused = out_state.fused or {}

    logger.info("Before await history.append assistant")
    await history.append(req.session_id, "assistant", final_answer)
    logger.info("After await history.append assistant")

    audit.add("request_end", {"route": "/chat"})

    m.close()

    # Ensure agent_results is awaited if it's a coroutine
    agent_results = out_state.agent_results
    if hasattr(agent_results, "__await__"):
        logger.info("Awaiting agent_results coroutine")
        agent_results = await agent_results
        logger.info("After awaiting agent_results")

    # Ensure fused is awaited if it's a coroutine
    if hasattr(fused, "__await__"):
        logger.info("Awaiting fused coroutine")
        fused = await fused
        logger.info("After awaiting fused")
    resp = ChatResponse(
        session_id=req.session_id,
        final_answer=final_answer,
        fused=fused,
        agent_results=agent_results,
        audit=(
            AuditBundle(events=audit.export()) if settings.enable_audit_trail else None
        ),
    )
    logger.info(f"{resp}")
    return ChatResponse(
        session_id=req.session_id,
        final_answer=final_answer,
        fused=fused,
        agent_results=agent_results,
        audit=(
            AuditBundle(events=audit.export()) if settings.enable_audit_trail else None
        ),
    )
