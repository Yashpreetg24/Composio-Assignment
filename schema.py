from pydantic import BaseModel, Field
from typing import List, Literal

class AppResearchResult(BaseModel):
    id: int = Field(description="The unique identifier for the app from the seed data")
    category: str = Field(description="The category of the app (given from seed data)")
    app: str = Field(description="The name of the app (given from seed data)")
    description: str = Field(description="One-line description of what the app does")
    auth_methods: List[str] = Field(description="Array of auth methods, e.g. ['OAuth2'], ['API key'], ['Basic Auth'], ['Token']")
    self_serve: Literal["self-serve", "gated-paid", "gated-approval", "gated-partnership"] = Field(
        description="Whether the API access is self-serve, gated behind a paid plan, requires approval, or requires a partnership."
    )
    api_surface: str = Field(
        description="Short text describing whether there's a documented public REST/GraphQL API, how broad it is, and whether an official MCP server already exists."
    )
    buildability_verdict: Literal["buildable-now", "buildable-with-friction", "not-buildable"] = Field(
        description="Verdict on how easily an integration can be built right now"
    )
    verdict_reason: str = Field(description="One-line reason/blocker for the buildability verdict")
    evidence_url: str = Field(description="The actual docs URL used to determine the information")
    confidence: Literal["high", "medium", "low"] = Field(description="How sure the agent is about the extracted information")
    needs_human_review: bool = Field(description="True if the agent couldn't find clear info or encountered an error")

