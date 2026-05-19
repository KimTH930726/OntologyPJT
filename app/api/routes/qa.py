from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.repositories.ai_query_log_repository import AIQueryLogRepository
from app.schemas.qa import (
    AIQueryLogResponse,
    DocumentEvidenceSummary,
    GraphContextSummary,
    QARequest,
    QAResponse,
)
from app.services.qa_service import LLMCallError, QAService

router = APIRouter(tags=["qa"])


@router.post("/qa", response_model=QAResponse)
def ask(payload: QARequest, db: Session = Depends(get_db)) -> QAResponse:
    svc = QAService(db)
    try:
        outcome = svc.answer(payload.question)
    except LLMCallError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "LLM_PROVIDER_FAILED",
                "message": str(e),
                "query_log_id": str(e.query_log_id),
            },
        ) from e

    return QAResponse(
        answer=outcome.answer,
        graph_context=GraphContextSummary(
            seed_entities=outcome.seed_entities,
            triple_count=outcome.triple_count,
        ),
        document_evidence=DocumentEvidenceSummary(chunk_count=outcome.chunk_count),
        query_log_id=outcome.query_log_id,
    )


@router.get("/qa/logs", response_model=list[AIQueryLogResponse])
def list_qa_logs(
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    contains_question: str | None = Query(default=None),
    model_provider: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[AIQueryLogResponse]:
    repo = AIQueryLogRepository(db)
    rows = repo.list(
        created_from=created_from,
        created_to=created_to,
        contains_question=contains_question,
        model_provider=model_provider,
        limit=limit,
        offset=offset,
    )
    return [AIQueryLogResponse.model_validate(r) for r in rows]


@router.get("/qa/logs/{id}", response_model=AIQueryLogResponse)
def get_qa_log(id: UUID, db: Session = Depends(get_db)) -> AIQueryLogResponse:
    repo = AIQueryLogRepository(db)
    row = repo.get(id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    return AIQueryLogResponse.model_validate(row)
