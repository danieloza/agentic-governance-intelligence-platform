from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RegressionCase
from app.policies import TOOL_SCOPE_MAP
from app.schemas import (
    RegressionCaseRequest,
    RegressionCaseResponse,
    RegressionCaseResult,
    RegressionRunRequest,
    RegressionRunResponse,
    VALID_SCOPES,
)

router = APIRouter(prefix="/regression", tags=["Regression Lab"])


def _evaluate_case(case: RegressionCase) -> tuple[str, str]:
    required_scope = TOOL_SCOPE_MAP.get(case.requested_tool)
    if required_scope is None:
        return "denied", "default_deny: unknown tool mapping"
    token_scopes = set(scope for scope in case.token_scopes.split(",") if scope)
    if required_scope not in token_scopes:
        return "denied", "default_deny: required scope missing from token"
    return "allowed", "allowed"


@router.post("/cases", response_model=RegressionCaseResponse, status_code=status.HTTP_201_CREATED, summary="Create regression case")
def create_case(payload: RegressionCaseRequest, db: Session = Depends(get_db)) -> RegressionCase:
    invalid = [scope for scope in payload.token_scopes if scope not in VALID_SCOPES]
    if invalid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"invalid_scopes": invalid})
    case = RegressionCase(
        tenant_id=payload.tenant_id,
        name=payload.name,
        agent_type=payload.agent_type,
        requested_tool=payload.requested_tool,
        token_scopes=",".join(payload.token_scopes),
        expected_decision=payload.expected_decision,
        expected_reason_contains=payload.expected_reason_contains,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("/cases", response_model=list[RegressionCaseResponse], summary="List regression cases")
def list_cases(tenant_id: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[RegressionCase]:
    query = select(RegressionCase).order_by(RegressionCase.created_at.desc(), RegressionCase.id.desc())
    if tenant_id:
        query = query.where(RegressionCase.tenant_id == tenant_id)
    return list(db.scalars(query).all())


@router.post("/run", response_model=RegressionRunResponse, summary="Run regression policy checks")
def run_regression(payload: RegressionRunRequest | None = None, db: Session = Depends(get_db)) -> RegressionRunResponse:
    query = select(RegressionCase).order_by(RegressionCase.id.asc())
    if payload and payload.tenant_id:
        query = query.where(RegressionCase.tenant_id == payload.tenant_id)
    cases = list(db.scalars(query).all())
    results: list[RegressionCaseResult] = []
    for case in cases:
        actual_decision, reason = _evaluate_case(case)
        passed = (
            actual_decision == case.expected_decision
            and case.expected_reason_contains.lower() in reason.lower()
        )
        results.append(
            RegressionCaseResult(
                case_id=case.id,
                name=case.name,
                expected_decision=case.expected_decision,
                actual_decision=actual_decision,
                reason=reason,
                passed=passed,
            )
        )
    passed_count = sum(1 for result in results if result.passed)
    return RegressionRunResponse(
        total_cases=len(results),
        passed=passed_count,
        failed=len(results) - passed_count,
        results=results,
    )
