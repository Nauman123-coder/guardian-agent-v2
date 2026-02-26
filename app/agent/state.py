"""
AgentState definition for the Guardian Threat Hunter.
Extended with incident tracking metadata for the web dashboard.
"""

from __future__ import annotations
from typing import Annotated, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    # Core fields — messages append-only, everything else is overwrite
    messages: Annotated[list[BaseMessage], operator.add]
    raw_log: str
    risk_score: int
    found_indicators: list[str]
    requires_approval: bool
    mitigation_plan: str
    executed_actions: list[str]
    investigation_results: list[dict[str, Any]]
    current_node: str

    # Identity fields — MUST be echoed by every node via _base(state)
    incident_id: str
    log_source: str
    status: str
    approval_token: str
    approval_decision: str
    started_at: str
    completed_at: str

    # stream_events: plain list (NOT Annotated) — nodes return full list each time
    stream_events: list[dict[str, Any]]