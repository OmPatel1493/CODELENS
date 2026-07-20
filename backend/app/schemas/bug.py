"""Bug-localization request/response schemas."""

from pydantic import BaseModel, Field


class BugLocalizeRequest(BaseModel):
    log_text: str = Field(min_length=1, max_length=20000)
    limit: int = Field(default=5, ge=1, le=15)


class ParsedLogOut(BaseModel):
    error_type: str | None
    message: str | None
    files: list[str]
    symbols: list[str]


class LocalizedFile(BaseModel):
    file_path: str
    score: float
    reason: str
    matched_symbols: list[str]
    snippet: str
    start_line: int
    end_line: int


class BugLocalizeResponse(BaseModel):
    parsed: ParsedLogOut
    results: list[LocalizedFile]
