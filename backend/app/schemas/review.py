"""AI code-review request/response schemas."""

from pydantic import BaseModel, Field, model_validator

from app.schemas.search import SearchHit


class ReviewRequest(BaseModel):
    # Provide exactly one: a raw unified diff, or a public GitHub PR URL.
    diff: str | None = Field(default=None, max_length=200_000)
    pr_url: str | None = Field(default=None, max_length=1024)

    @model_validator(mode="after")
    def _one_source(self) -> "ReviewRequest":
        if bool(self.diff and self.diff.strip()) == bool(self.pr_url and self.pr_url.strip()):
            raise ValueError("Provide exactly one of `diff` or `pr_url`.")
        return self


class ReviewComment(BaseModel):
    # high | medium | low | nit — free-form but the prompt constrains it.
    severity: str
    file: str | None = None
    line: int | None = None
    comment: str


class ReviewResponse(BaseModel):
    # One-line verdict/summary of the change.
    summary: str
    comments: list[ReviewComment]
    # Repo chunks retrieved as context — [n] citations in comments map to these.
    sources: list[SearchHit]
