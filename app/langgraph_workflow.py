from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Interrupt, interrupt
from pydantic import BaseModel, Field

from app.audit import write_audit_log
from app.auth import decode_scoped_token
from app.config import get_settings
from app.database import SessionLocal
from app.graph import record_governed_tool_call
from app.incidents import create_incident
from app.models import Agent, PolicyDecisionRecord, ToolCall
from app.policies import evaluate_tool_access
from app.redaction import redact_pii
from app.tools import (
    brand_analyze_market_signals,
    brand_create_report,
    dev_propose_patch,
    dev_read_repo_file,
    dev_run_test,
    finance_create_expense_review,
    finance_get_invoice_summary,
    hr_search_employee_policy,
    legal_search_contract_clause,
    legal_summarize_contract_risk,
    mcp_invoke_tool,
    ops_create_report,
)

settings = get_settings()
router = APIRouter(prefix="/workflows/langgraph", tags=["LangGraph Workflows"])


class GovernanceWorkflowState(TypedDict, total=False):
    thread_id: str
    tenant_id: str
    agent_id: int
    owner_user_id: str
    token_payload: dict[str, Any]
    tool_name: str
    arguments: dict[str, Any]
    required_scope: str
    risk_level: str
    policy_allowed: bool
    policy_reason: str
    human_approved: bool | None
    approved_by: str | None
    reviewer_note: str | None
    status: str
    result: dict[str, Any] | None
    timeline: Annotated[list[str], operator.add]


class WorkflowStartRequest(BaseModel):
    access_token: str = Field(min_length=20)
    tenant_id: str = Field(min_length=2, max_length=120)
    tool_name: str = Field(min_length=2, max_length=160)
    arguments: dict[str, Any] = Field(default_factory=dict)
    thread_id: str | None = Field(default=None, min_length=4, max_length=160)


class WorkflowResumeRequest(BaseModel):
    approved: bool
    reviewed_by: str = Field(min_length=2, max_length=255)
    note: str = Field(default="", max_length=1000)


class WorkflowResponse(BaseModel):
    thread_id: str
    status: Literal["completed", "denied", "awaiting_human_approval"]
    tool_name: str
    required_scope: str
    risk_level: str
    policy_reason: str
    result: dict[str, Any] | None
    timeline: list[str]
    approval_request: dict[str, Any] | None = None


TOOL_EXECUTORS = {
    "hr.search_employee_policy": hr_search_employee_policy,
    "finance.get_invoice_summary": finance_get_invoice_summary,
    "finance.create_expense_review": finance_create_expense_review,
    "legal.search_contract_clause": legal_search_contract_clause,
    "legal.summarize_contract_risk": legal_summarize_contract_risk,
    "ops.create_report": ops_create_report,
    "mcp.invoke_tool": mcp_invoke_tool,
    "brand.analyze_market_signals": brand_analyze_market_signals,
    "brand.create_report": brand_create_report,
    "dev.read_repo_file": dev_read_repo_file,
    "dev.propose_patch": dev_propose_patch,
    "dev.run_test": dev_run_test,
}


def _record_policy_decision(state: GovernanceWorkflowState) -> None:
    with SessionLocal() as db:
        db.add(
            PolicyDecisionRecord(
                tenant_id=state["tenant_id"],
                agent_id=state["agent_id"],
                tool_name=state["tool_name"],
                required_scope=state["required_scope"],
                allowed=state["policy_allowed"],
                reason=state["policy_reason"],
                risk_level=state["risk_level"],
                policy_version=settings.policy_version,
                pii_redaction_required=True,
            )
        )
        db.commit()


def _record_tool_call(
    state: GovernanceWorkflowState,
    *,
    decision: str,
    reason: str,
    output_preview: str | None = None,
) -> ToolCall:
    with SessionLocal() as db:
        call = ToolCall(
            tenant_id=state["tenant_id"],
            agent_id=state["agent_id"],
            tool_name=state["tool_name"],
            required_scope=state["required_scope"],
            decision=decision,
            reason=reason,
            risk_level=state["risk_level"],
            policy_version=settings.policy_version,
            pii_redacted=True,
            output_preview=output_preview,
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return call


def evaluate_policy_node(state: GovernanceWorkflowState) -> dict[str, Any]:
    with SessionLocal() as db:
        agent = db.get(Agent, state["agent_id"])
        decision = evaluate_tool_access(
            agent=agent,
            token_payload=state["token_payload"],
            tool_name=state["tool_name"],
            policy_version=settings.policy_version,
        )

    update = {
        "required_scope": decision.required_scope,
        "risk_level": decision.risk_level,
        "policy_allowed": decision.allowed,
        "policy_reason": decision.reason,
        "status": "policy_allowed" if decision.allowed else "denied",
        "timeline": [
            f"policy:{'allowed' if decision.allowed else 'denied'}:{decision.reason}",
        ],
    }
    _record_policy_decision({**state, **update})
    return update


def route_after_policy(state: GovernanceWorkflowState) -> Literal["request_human_approval", "execute_tool", "record_policy_denial"]:
    if not state["policy_allowed"]:
        return "record_policy_denial"
    if state["risk_level"] == "high":
        return "request_human_approval"
    return "execute_tool"


def request_human_approval_node(state: GovernanceWorkflowState) -> dict[str, Any]:
    review = interrupt(
        {
            "type": "high_risk_tool_approval",
            "thread_id": state["thread_id"],
            "agent_id": state["agent_id"],
            "tool_name": state["tool_name"],
            "required_scope": state["required_scope"],
            "risk_level": state["risk_level"],
            "arguments_preview": redact_pii(state["arguments"]),
            "policy_reason": state["policy_reason"],
        }
    )
    return {
        "human_approved": bool(review["approved"]),
        "approved_by": review["reviewed_by"],
        "reviewer_note": review.get("note", ""),
        "timeline": [
            f"human_review:{'approved' if review['approved'] else 'rejected'}:{review['reviewed_by']}",
        ],
    }


def route_after_human_review(state: GovernanceWorkflowState) -> Literal["execute_tool", "record_human_denial"]:
    return "execute_tool" if state.get("human_approved") else "record_human_denial"


def execute_tool_node(state: GovernanceWorkflowState) -> dict[str, Any]:
    executor = TOOL_EXECUTORS.get(state["tool_name"])
    if executor is None:
        raise ValueError(f"No executor registered for {state['tool_name']}")

    try:
        raw_result = executor(**state["arguments"])
    except TypeError as exc:
        raise ValueError(f"Invalid arguments for {state['tool_name']}: {exc}") from exc

    result = redact_pii(raw_result)
    _record_tool_call(state, decision="allowed", reason="langgraph workflow completed", output_preview=str(result)[:600])

    with SessionLocal() as db:
        write_audit_log(
            db,
            tenant_id=state["tenant_id"],
            agent_id=state["agent_id"],
            owner_user_id=state["owner_user_id"],
            action="langgraph_tool_executed",
            tool_name=state["tool_name"],
            requested_scope=state["required_scope"],
            decision="allowed",
            reason="Tool executed after policy and human-review routing",
            risk_level=state["risk_level"],
        )
        record_governed_tool_call(
            db,
            tenant_id=state["tenant_id"],
            agent_id=state["agent_id"],
            owner_user_id=state["owner_user_id"],
            tool_name=state["tool_name"],
            scope=state["required_scope"],
            output_type="langgraph_tool_output",
            output_id=f"{state['thread_id']}:{state['tool_name']}",
        )

    return {
        "status": "completed",
        "result": result,
        "timeline": [f"tool:executed:{state['tool_name']}", "workflow:completed"],
    }


def record_policy_denial_node(state: GovernanceWorkflowState) -> dict[str, Any]:
    call = _record_tool_call(state, decision="denied", reason=state["policy_reason"])
    with SessionLocal() as db:
        write_audit_log(
            db,
            tenant_id=state["tenant_id"],
            agent_id=state["agent_id"],
            owner_user_id=state["owner_user_id"],
            action="langgraph_policy_denied",
            tool_name=state["tool_name"],
            requested_scope=state["required_scope"],
            decision="denied",
            reason=state["policy_reason"],
            risk_level=state["risk_level"],
        )
        create_incident(
            db,
            tenant_id=state["tenant_id"],
            agent_id=state["agent_id"],
            severity=state["risk_level"],
            title=f"LangGraph policy denial: {state['tool_name']}",
            description=f"Governed workflow denied access to {state['tool_name']}.",
            policy_reason=state["policy_reason"],
            related_tool_call_id=call.id,
        )
    return {"status": "denied", "result": None, "timeline": ["workflow:denied_by_policy"]}


def record_human_denial_node(state: GovernanceWorkflowState) -> dict[str, Any]:
    reason = f"human review rejected by {state['approved_by']}: {state.get('reviewer_note') or 'no note'}"
    _record_tool_call(state, decision="denied", reason=reason)
    with SessionLocal() as db:
        write_audit_log(
            db,
            tenant_id=state["tenant_id"],
            agent_id=state["agent_id"],
            owner_user_id=state["owner_user_id"],
            action="langgraph_human_rejected",
            tool_name=state["tool_name"],
            requested_scope=state["required_scope"],
            decision="denied",
            reason=reason,
            risk_level=state["risk_level"],
        )
    return {"status": "denied", "result": None, "timeline": ["workflow:denied_by_human"]}


def build_governance_graph():
    builder = StateGraph(GovernanceWorkflowState)
    builder.add_node("evaluate_policy", evaluate_policy_node)
    builder.add_node("request_human_approval", request_human_approval_node)
    builder.add_node("execute_tool", execute_tool_node)
    builder.add_node("record_policy_denial", record_policy_denial_node)
    builder.add_node("record_human_denial", record_human_denial_node)

    builder.add_edge(START, "evaluate_policy")
    builder.add_conditional_edges("evaluate_policy", route_after_policy)
    builder.add_conditional_edges("request_human_approval", route_after_human_review)
    builder.add_edge("execute_tool", END)
    builder.add_edge("record_policy_denial", END)
    builder.add_edge("record_human_denial", END)
    return builder.compile(checkpointer=MemorySaver())


governance_graph = build_governance_graph()


def _serialize_interrupt(interrupts: tuple[Interrupt, ...]) -> dict[str, Any] | None:
    if not interrupts:
        return None
    value = interrupts[0].value
    return value if isinstance(value, dict) else {"message": str(value)}


def _response(thread_id: str, result: dict[str, Any]) -> WorkflowResponse:
    state = governance_graph.get_state({"configurable": {"thread_id": thread_id}})
    values = dict(state.values)
    approval_request = _serialize_interrupt(result.get("__interrupt__", ()))
    current_status = "awaiting_human_approval" if approval_request else values.get("status", "denied")
    return WorkflowResponse(
        thread_id=thread_id,
        status=current_status,
        tool_name=values["tool_name"],
        required_scope=values.get("required_scope", ""),
        risk_level=values.get("risk_level", "high"),
        policy_reason=values.get("policy_reason", ""),
        result=values.get("result"),
        timeline=values.get("timeline", []),
        approval_request=approval_request,
    )


@router.post("/start", response_model=WorkflowResponse, summary="Start a governed LangGraph tool workflow")
def start_workflow(payload: WorkflowStartRequest) -> WorkflowResponse:
    token_payload = decode_scoped_token(payload.access_token)
    if token_payload.get("tenant_id") != payload.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token tenant does not match request tenant")

    thread_id = payload.thread_id or f"governance-{uuid4()}"
    existing = governance_graph.get_state({"configurable": {"thread_id": thread_id}})
    if existing.values:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workflow thread already exists; resume it or use a new thread_id",
        )
    initial_state: GovernanceWorkflowState = {
        "thread_id": thread_id,
        "tenant_id": payload.tenant_id,
        "agent_id": int(token_payload["agent_id"]),
        "owner_user_id": token_payload["owner_user_id"],
        "token_payload": token_payload,
        "tool_name": payload.tool_name,
        "arguments": payload.arguments,
        "human_approved": None,
        "status": "started",
        "result": None,
        "timeline": ["workflow:started"],
    }
    try:
        result = governance_graph.invoke(initial_state, {"configurable": {"thread_id": thread_id}})
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _response(thread_id, result)


@router.post("/{thread_id}/resume", response_model=WorkflowResponse, summary="Resume a paused LangGraph approval workflow")
def resume_workflow(thread_id: str, payload: WorkflowResumeRequest) -> WorkflowResponse:
    snapshot = governance_graph.get_state({"configurable": {"thread_id": thread_id}})
    if not snapshot.values:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow thread not found")
    if not snapshot.next:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow is not waiting for approval")

    result = governance_graph.invoke(
        Command(resume={"approved": payload.approved, "reviewed_by": payload.reviewed_by, "note": payload.note}),
        {"configurable": {"thread_id": thread_id}},
    )
    return _response(thread_id, result)


@router.get("/{thread_id}", response_model=WorkflowResponse, summary="Inspect a LangGraph workflow checkpoint")
def get_workflow(thread_id: str) -> WorkflowResponse:
    snapshot = governance_graph.get_state({"configurable": {"thread_id": thread_id}})
    if not snapshot.values:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow thread not found")
    approval_request = None
    if snapshot.next:
        approval_request = {
            "type": "high_risk_tool_approval",
            "message": "Workflow is paused at a human approval interrupt.",
        }
    return WorkflowResponse(
        thread_id=thread_id,
        status="awaiting_human_approval" if snapshot.next else snapshot.values.get("status", "denied"),
        tool_name=snapshot.values["tool_name"],
        required_scope=snapshot.values.get("required_scope", ""),
        risk_level=snapshot.values.get("risk_level", "high"),
        policy_reason=snapshot.values.get("policy_reason", ""),
        result=snapshot.values.get("result"),
        timeline=snapshot.values.get("timeline", []),
        approval_request=approval_request,
    )


@router.get("", summary="Describe the governed LangGraph workflow")
def describe_workflow() -> dict[str, Any]:
    return {
        "name": "Governed high-risk tool workflow",
        "runtime": "LangGraph",
        "state_model": "GovernanceWorkflowState",
        "checkpointer": "MemorySaver (demo); use a durable database-backed checkpointer in production",
        "nodes": [
            {"id": "evaluate_policy", "purpose": "Run deterministic default-deny scope and tenant checks"},
            {"id": "request_human_approval", "purpose": "Pause high-risk execution with LangGraph interrupt()"},
            {"id": "execute_tool", "purpose": "Execute a mock-safe governed tool and redact output"},
            {"id": "record_policy_denial", "purpose": "Persist policy denial, audit evidence and incident"},
            {"id": "record_human_denial", "purpose": "Persist the operator rejection and audit evidence"},
        ],
        "routes": [
            "policy denied -> record_policy_denial -> END",
            "policy allowed + low/medium risk -> execute_tool -> END",
            "policy allowed + high risk -> request_human_approval",
            "human approved -> execute_tool -> END",
            "human rejected -> record_human_denial -> END",
        ],
        "capabilities": [
            "explicit state",
            "conditional edges",
            "checkpoint inspection",
            "human-in-the-loop interrupt and resume",
            "policy reuse",
            "audit logs",
            "PII and secret redaction",
            "tool-call and graph relationship records",
        ],
    }
