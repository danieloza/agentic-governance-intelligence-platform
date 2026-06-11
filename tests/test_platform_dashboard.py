def test_platform_overview_exposes_connected_modules(client):
    response = client.get("/platform/overview")

    assert response.status_code == 200
    payload = response.json()
    module_keys = {module["key"] for module in payload["modules"]}
    assert payload["metrics"]["modules"] == 9
    assert "automation-control-plane" in module_keys
    assert "agent-runtime-control-tower" in module_keys
    assert "llm-incident-review-console" in module_keys
    assert "agent-regression-lab" in module_keys
    assert "agent-intel-mcp" in module_keys
    assert "inference-readiness-advisor" in module_keys


def test_platform_runtime_metrics_are_computed(client):
    response = client.get("/platform/runtime")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["completed"] == 3
    assert payload["metrics"]["blocked"] == 1
    assert payload["metrics"]["total_tool_calls"] == 29
    assert payload["metrics"]["avg_latency_ms"] > 0


def test_platform_overview_uses_real_seeded_audit_data(client):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "dashboard-tenant",
            "agent_name": "Dashboard Brand Agent",
            "agent_type": "brand-intel-agent",
            "requested_scopes": ["brand:insight:read"],
            "reason": "Dashboard metric proof",
            "owner_user_id": "dashboard.owner",
        },
    ).json()
    client.post(
        f"/agent-auth/approve/{registration['agent_id']}",
        json={"approved_scopes": ["brand:insight:read"], "approved_by": "dashboard.admin", "expires_in_hours": 8},
    )
    token = client.post("/agent-auth/token", json={"agent_id": registration["agent_id"]}).json()["access_token"]
    client.post(
        "/tools/brand/analyze_market_signals",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "dashboard-tenant"},
        json={
            "brand_name": "AcmeFlow",
            "competitor_names": ["Northwind AI"],
            "signals": ["Competitor changed support messaging"],
        },
    )
    client.post(
        "/tools/brand/create_report",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "dashboard-tenant"},
        json={"brand_name": "AcmeFlow", "report_name": "Denied report", "insight_ids": ["BI-1"]},
    )

    response = client.get("/platform/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["total_agents"] == 1
    assert payload["metrics"]["policy_violations"] >= 1
    assert payload["metrics"]["graph_edges"] >= 5
    assert len(payload["activity_series"]) == 7
    assert len(payload["scope_distribution"]) >= 10


def test_dashboard_shell_contains_all_sidebar_sections(client):
    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert "Governance Overview" in html
    assert "Agents" in html
    assert "Tool Gateway" in html
    assert "Policy Decisions" in html
    assert "Incidents" in html
    assert "Regression Lab" in html
    assert "Audit Explorer" in html
    assert "OpenAPI Console" in html
    assert "Observability" in html
    assert 'aria-label="Global search"' in html
    assert 'id="search-results"' in html
