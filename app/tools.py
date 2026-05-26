from __future__ import annotations

from typing import Any


def hr_search_employee_policy(employee_query: str) -> dict[str, Any]:
    return {
        "employee_query": employee_query,
        "matching_policy": {
            "policy_id": "HR-001",
            "title": "Remote Work Policy",
            "summary": "Employees may work remotely up to three days per week with manager approval.",
            "contact": {
                "full_name": "Anna Kowalska",
                "email": "anna.kowalska@company.example",
                "phone": "+48 555 000 111",
            },
        },
    }


def finance_get_invoice_summary(invoice_id: str) -> dict[str, Any]:
    return {
        "invoice_id": invoice_id,
        "vendor_name": "Northwind Logistics",
        "amount": 18450.25,
        "currency": "PLN",
        "status": "pending approval",
        "approver": {
            "full_name": "Jan Nowak",
            "email": "jan.nowak@company.example",
        },
        "bank_account": "11 2222 3333 4444 5555 6666 7777",
    }


def finance_create_expense_review(expense_title: str, amount: float, currency: str) -> dict[str, Any]:
    return {
        "expense_title": expense_title,
        "amount": amount,
        "currency": currency,
        "review_case_id": "EXP-REV-2026-001",
        "submitted_by": {
            "full_name": "Maria Wisniewska",
            "email": "maria.wisniewska@company.example",
        },
        "status": "queued_for_review",
    }


def legal_search_contract_clause(contract_id: str, clause_query: str) -> dict[str, Any]:
    return {
        "contract_id": contract_id,
        "clause_query": clause_query,
        "clause_result": {
            "section": "9.2",
            "excerpt": "Either party may terminate with 30 days written notice for repeated material breach.",
            "counterparty_contact": {
                "full_name": "Adam Zielinski",
                "email": "adam.zielinski@partner.example",
                "address": "Warsaw, Example Street 1",
            },
        },
    }


def legal_summarize_contract_risk(contract_id: str) -> dict[str, Any]:
    return {
        "contract_id": contract_id,
        "risk_level": "medium",
        "summary": [
            "Termination rights are asymmetrical in favor of the supplier.",
            "Liability cap excludes delayed delivery penalties.",
            "Data processing annex references personal identifiers."
        ],
        "risk_owner": {
            "full_name": "Ewa Maj",
            "email": "ewa.maj@company.example",
            "personal_id": "ABC123456",
        },
    }


def ops_create_report(report_name: str, department: str) -> dict[str, Any]:
    return {
        "report_name": report_name,
        "department": department,
        "report_id": "OPS-REP-2026-014",
        "status": "created",
        "owner": {
            "full_name": "Piotr Wrobel",
            "email": "piotr.wrobel@company.example",
        },
    }


def mcp_invoke_tool(
    *,
    mcp_server_id: str,
    tool_name: str,
    justification: str,
    estimated_tokens: int,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    risk_level = "high" if any(word in tool_name for word in ["write", "delete", "deploy", "payment"]) else "medium"
    return {
        "mcp_request_id": f"MCP-{abs(hash((mcp_server_id, tool_name, justification))) % 100000:05d}",
        "mcp_server_id": mcp_server_id,
        "tool_name": tool_name,
        "decision": "routed_to_gateway",
        "risk_level": risk_level,
        "estimated_tokens": estimated_tokens,
        "justification": justification,
        "sanitized_arguments": arguments,
        "approval_required": risk_level == "high",
        "operator_note": "The MCP tool was invoked through the governed gateway boundary.",
    }


def brand_analyze_market_signals(
    *,
    brand_name: str,
    competitor_names: list[str],
    signals: list[str],
) -> dict[str, Any]:
    normalized_signals = [signal.strip() for signal in signals if signal.strip()]
    competitor_names = [name.strip() for name in competitor_names if name.strip()]
    insight_id = f"BI-{abs(hash((brand_name, tuple(normalized_signals)))) % 100000:05d}"
    opportunities = []
    for signal in normalized_signals:
        lower_signal = signal.lower()
        if "price" in lower_signal or "pricing" in lower_signal:
            opportunities.append("clarify pricing and packaging")
        elif "support" in lower_signal:
            opportunities.append("highlight support response quality")
        elif "setup" in lower_signal or "onboarding" in lower_signal:
            opportunities.append("position onboarding simplicity")
        else:
            opportunities.append("review messaging for recurring market signal")

    return {
        "insight_id": insight_id,
        "brand_name": brand_name,
        "competitors": competitor_names,
        "signals_analyzed": len(normalized_signals),
        "positioning_signals": sorted(set(opportunities)),
        "summary": "Structured market signals were converted into explainable brand insight candidates.",
        "review_owner": {
            "full_name": "Marketing Analyst",
            "email": "marketing.analyst@company.example",
        },
    }


def brand_create_report(*, brand_name: str, report_name: str, insight_ids: list[str]) -> dict[str, Any]:
    report_id = f"BR-{abs(hash((brand_name, report_name, tuple(insight_ids)))) % 100000:05d}"
    return {
        "report_id": report_id,
        "brand_name": brand_name,
        "report_name": report_name,
        "insight_ids": insight_ids,
        "status": "queued_for_human_review",
        "sections": ["market changes", "competitor signals", "positioning opportunities", "recommended review items"],
        "prepared_for": {
            "full_name": "Product Marketing Lead",
            "email": "product.marketing@company.example",
        },
    }


def dev_read_repo_file(path: str) -> dict[str, Any]:
    return {
        "path": path,
        "mode": "mock_read_only",
        "content_excerpt": "Mock repository file preview returned through the governed tool gateway.",
        "sensitive_notice": "Raw secrets, tokens and credentials are not returned by this tool.",
    }


def dev_propose_patch(path: str, patch_summary: str) -> dict[str, Any]:
    return {
        "path": path,
        "patch_id": f"PATCH-{abs(hash((path, patch_summary))) % 100000:05d}",
        "status": "proposed_for_human_review",
        "patch_summary": patch_summary,
        "requires_approval": True,
        "operator_note": "Patch proposal is captured as a reviewable artifact; the gateway does not apply changes directly.",
    }


def dev_run_test(test_command: str) -> dict[str, Any]:
    return {
        "test_command": test_command,
        "run_id": f"TEST-{abs(hash(test_command)) % 100000:05d}",
        "status": "completed",
        "passed": True,
        "summary": "Mock test execution completed through controlled dev tooling.",
        "logs": "12 passed, 0 failed",
    }
