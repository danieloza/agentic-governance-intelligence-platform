from __future__ import annotations

import json
from uuid import uuid4

import httpx

BASE_URL = "http://127.0.0.1:8000"
TENANT_ID = "langgraph-demo"


def show(label: str, response: httpx.Response) -> dict:
    response.raise_for_status()
    payload = response.json()
    print(f"\n--- {label} ---")
    print(json.dumps(payload, indent=2))
    return payload


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        registration = show(
            "register agent",
            client.post(
                "/agent-auth/register",
                json={
                    "tenant_id": TENANT_ID,
                    "agent_name": "LangGraph Patch Agent",
                    "agent_type": "stateful_workflow_agent",
                    "requested_scopes": ["dev:patch:propose"],
                    "reason": "Demonstrate a governed high-risk tool workflow",
                    "owner_user_id": "demo-owner",
                },
            ),
        )
        agent_id = registration["agent_id"]

        show(
            "approve scope",
            client.post(
                f"/agent-auth/approve/{agent_id}",
                json={
                    "approved_scopes": ["dev:patch:propose"],
                    "approved_by": "platform-admin",
                    "expires_in_hours": 8,
                },
            ),
        )
        token_response = client.post("/agent-auth/token", json={"agent_id": agent_id})
        token_response.raise_for_status()
        token = token_response.json()["access_token"]
        print("\n--- issue scoped token ---")
        print('{"status": "issued", "token": "[REDACTED]"}')

        thread_id = f"interview-langgraph-demo-{uuid4()}"
        show(
            "start workflow - pauses for human approval",
            client.post(
                "/workflows/langgraph/start",
                json={
                    "thread_id": thread_id,
                    "access_token": token,
                    "tenant_id": TENANT_ID,
                    "tool_name": "dev.propose_patch",
                    "arguments": {
                        "path": "README.md",
                        "patch_summary": "Document the governed LangGraph approval workflow",
                    },
                },
            ),
        )

        show(
            "resume workflow - operator approves",
            client.post(
                f"/workflows/langgraph/{thread_id}/resume",
                json={
                    "approved": True,
                    "reviewed_by": "security-reviewer",
                    "note": "Documentation-only change approved",
                },
            ),
        )
        show("inspect audit evidence", client.get(f"/agent-auth/audit?agent_id={agent_id}&tool_name=dev.propose_patch"))


if __name__ == "__main__":
    main()
