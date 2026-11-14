import os
import secrets
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.security import APIKeyHeader
from sqlmodel import Session, select

from ai_service import AICodeReviewer, AIServiceError
from database import create_db_and_tables, get_session
from models import CodeReviewRecord, CodeReviewRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Smart Code Reviewer API",
    description="Reviews code snippets for security problems, including accidentally leaked API keys.",
    lifespan=lifespan,
)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided: str | None = Security(_api_key_header)) -> None:
    """If API_KEY is set in the environment, every request must send it in
    the X-API-Key header. If it is not set, the API stays open (local dev)."""
    expected = os.getenv("API_KEY")
    if not expected:
        return
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@lru_cache
def get_reviewer() -> AICodeReviewer:
    # Created lazily so importing the app (e.g. in tests) never needs a real key.
    return AICodeReviewer()


@app.post(
    "/analyze",
    response_model=CodeReviewRecord,
    dependencies=[Depends(require_api_key)],
)
def analyze_and_save_code(
    request: CodeReviewRequest,
    session: Session = Depends(get_session),
    reviewer: AICodeReviewer = Depends(get_reviewer),
):
    try:
        analysis_result = reviewer.analyze_code(
            code=request.code_snippet,
            language=request.language,
        )
    except AIServiceError:
        # Nothing is saved when the AI call fails.
        raise HTTPException(status_code=502, detail="AI analysis failed, please try again.")

    db_record = CodeReviewRecord(
        code_snippet=request.code_snippet,
        language=request.language,
        security_status=analysis_result["security_status"],
        ai_feedback=analysis_result["ai_feedback"],
    )

    session.add(db_record)
    session.commit()
    session.refresh(db_record)

    return db_record


@app.get(
    "/history",
    response_model=List[CodeReviewRecord],
    dependencies=[Depends(require_api_key)],
)
def get_review_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    statement = (
        select(CodeReviewRecord)
        .order_by(CodeReviewRecord.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return session.exec(statement).all()
