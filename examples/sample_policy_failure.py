from __future__ import annotations

import requests

BASE_URL = "http://127.0.0.1:8015"


def main() -> None:
    registration = requests.post(
        f"{BASE_URL}/agent-auth/register",
        json={
            "tenant_id": "demo-policy-failure",
            "agent_name": "Ops Agent Without Finance Scope",
            "agent_type": "workflow_agent",
            "requested_scopes": ["ops:report:create"],
            "reason": "Demonstrate a denied tool call and incident creation",
            "owner_user_id": "demo.operator",
        },
        timeout=10,
    )
    registration.raise_for_status()
    agent_id = registration.json()["agent_id"]

    approval = requests.post(
        f"{BASE_URL}/agent-auth/approve/{agent_id}",
        json={
            "approved_scopes": ["ops:report:create"],
            "approved_by": "demo.admin",
            "expires_in_hours": 4,
        },
        timeout=10,
    )
    approval.raise_for_status()

    token_response = requests.post(f"{BASE_URL}/agent-auth/token", json={"agent_id": agent_id}, timeout=10)
    token_response.raise_for_status()
    token = token_response.json()["access_token"]

    denied = requests.post(
        f"{BASE_URL}/tools/finance/get_invoice_summary",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "demo-policy-failure"},
        json={"invoice_id": "INV-DEMO-001"},
        timeout=10,
    )
    print("Denied status:", denied.status_code)
    print("Denied payload:", denied.json())

    incidents = requests.get(f"{BASE_URL}/incidents?tenant_id=demo-policy-failure", timeout=10)
    incidents.raise_for_status()
    print("Incidents:", incidents.json())


if __name__ == "__main__":
    main()
