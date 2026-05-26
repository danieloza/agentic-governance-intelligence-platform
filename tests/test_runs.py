def _register_agent(client):
    registration = client.post(
        "/agent-auth/register",
        json={
            "tenant_id": "tenant-runs",
            "agent_name": "Run Agent",
            "agent_type": "workflow_agent",
            "requested_scopes": ["ops:report:create"],
            "reason": "Run lifecycle test",
            "owner_user_id": "owner-runs",
        },
    ).json()
    return registration["agent_id"]


def test_run_start_and_finish(client):
    agent_id = _register_agent(client)

    start = client.post("/runs/start", json={"agent_id": agent_id, "objective": "Create weekly operations report"})
    assert start.status_code == 201
    run = start.json()
    assert run["status"] == "running"
    assert run["agent_id"] == agent_id

    finish = client.post(f"/runs/{run['id']}/finish", json={"status": "completed", "risk_score": 12})
    assert finish.status_code == 200
    finished = finish.json()
    assert finished["status"] == "completed"
    assert finished["finished_at"] is not None


def test_list_and_get_runs(client):
    agent_id = _register_agent(client)
    run = client.post("/runs/start", json={"agent_id": agent_id, "objective": "Review policy-safe workflow"}).json()

    listed = client.get(f"/runs?agent_id={agent_id}")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == run["id"]

    detail = client.get(f"/runs/{run['id']}")
    assert detail.status_code == 200
    assert detail.json()["objective"] == "Review policy-safe workflow"
