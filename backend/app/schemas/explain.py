"""Plain-English "Explain" request/response schemas (for non-technical users)."""

from pydantic import BaseModel, Field, model_validator


class ExplainRequest(BaseModel):
    # "repo" = explain the whole project; "file" = explain one file (needs `file`).
    scope: str = Field(pattern="^(repo|file)$")
    file: str | None = Field(default=None, max_length=1024)

    @model_validator(mode="after")
    def _file_required_for_file_scope(self) -> "ExplainRequest":
        if self.scope == "file" and not (self.file and self.file.strip()):
            raise ValueError("scope 'file' requires a `file` path.")
        return self


class ExplainSection(BaseModel):
    heading: str  # a plain-English heading
    body: str  # everyday-language explanation


class GlossaryItem(BaseModel):
    term: str  # a technical word that couldn't be avoided
    definition: str  # a one-line, jargon-free definition


class ExplainResponse(BaseModel):
    scope: str
    title: str  # friendly title, e.g. "What this project does"
    summary: str  # 2-3 sentence plain-English overview
    sections: list[ExplainSection]
    glossary: list[GlossaryItem]
