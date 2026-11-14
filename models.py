import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import field_validator
from sqlmodel import SQLModel, Field

MAX_CODE_LENGTH = 20_000
_LANGUAGE_PATTERN = re.compile(r"^[A-Za-z0-9+#.\-]{1,30}$")


class SecurityStatus(str, Enum):
    SAFE = "Safe"
    LOW_RISK = "Low Risk"
    HIGH_RISK = "High Risk"
    CRITICAL = "Critical Vulnerability"


class CodeReviewRequest(SQLModel):
    code_snippet: str
    language: str = "python"

    @field_validator("code_snippet")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("code_snippet must not be empty")
        if len(value) > MAX_CODE_LENGTH:
            raise ValueError(f"code_snippet must be at most {MAX_CODE_LENGTH} characters")
        return value

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        # `language` is placed inside the LLM prompt, so only allow short,
        # plain language names (python, c++, c#, javascript, ...).
        value = value.strip()
        if not _LANGUAGE_PATTERN.fullmatch(value):
            raise ValueError("language must be 1-30 chars: letters, digits, + # . -")
        return value


class CodeReviewRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code_snippet: str
    language: str
    security_status: str
    ai_feedback: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
