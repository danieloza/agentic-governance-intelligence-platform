import requests


BASE_URL = "http://127.0.0.1:8000"


def main() -> None:
    registration = requests.post(
        f"{BASE_URL}/agent-auth/register",
        json={
            "agent_name": "Example HR Agent",
            "agent_type": "hr-agent",
            "requested_scopes": ["hr:policy:read"],
            "reason": "Need policy search inside onboarding workflow",
            "owner_user_id": "user-123",
        },
        timeout=15,
    )
    print("Registration:", registration.json())
    print("Approve manually through /agent-auth/approve/{agent_id} before requesting token.")


if __name__ == "__main__":
    main()

