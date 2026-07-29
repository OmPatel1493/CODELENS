"""Dependency-graph response schemas."""

from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str  # repo-relative file path
    label: str  # file basename
    group: str  # top-level directory (for coloring)
    in_degree: int  # how many files import this one (hub size)


class GraphEdge(BaseModel):
    source: str  # importer file path
    target: str  # imported file path


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncated: bool  # true if the graph was capped for legibility
