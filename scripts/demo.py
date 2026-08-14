#!/usr/bin/env python3
"""
End-to-end demo of the agent deployment lifecycle.

This script demonstrates:
1. User authentication
2. Agent registration
3. Approval workflow
4. Deployment
5. Monitoring
6. Rollback (if needed)
"""

import asyncio
import time
from typing import Any

import httpx


BASE_URL = "http://localhost:8000"


async def print_step(step: str, description: str) -> None:
    """Print a formatted step header."""
    print()
    print("=" * 70)
    print(f"STEP {step}: {description}")
    print("=" * 70)
    print()


async def print_response(response: httpx.Response) -> None:
    """Print formatted response."""
    status_color = "\033[92m" if response.status_code < 400 else "\033[91m"
    reset = "\033[0m"
    print(f"{status_color}Status: {response.status_code}{reset}")
    try:
        data = response.json()
        import json

        print(json.dumps(data, indent=2))
    except Exception:
        print(response.text)


async def run_demo() -> None:
    """Run the complete demo."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        print()
        print("╔" + "═" * 68 + "╗")
        print("║" + " " * 10 + "Enterprise Agent Orchestrator - E2E Demo" + " " * 17 + "║")
        print("╚" + "═" * 68 + "╝")

        # Step 1: Authenticate
        await print_step("1", "Authenticate as Developer")

        login_response = await client.post(
            "/users/login",
            json={"email": "developer@demo.com", "password": "dev123"},
        )
        await print_response(login_response)

        if login_response.status_code != 200:
            print("\n✗ Authentication failed. Make sure to run seed_demo_data.py first.")
            return

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print("\n✓ Successfully authenticated as developer@demo.com")

        # Step 2: Create a new agent
        await print_step("2", "Register a New Agent")

        agent_data = {
            "name": "Demo Customer Support Agent",
            "description": "AI agent for automated customer support ticket triage",
            "agent_type": "support",
            "capabilities": {
                "actions": ["classify_ticket", "suggest_response", "escalate"]
            },
            "configuration": {
                "runtime": "python",
                "resources": {"memory_mb": 512, "cpu_cores": 1},
                "data_access": {
                    "classification": "internal",
                    "pii_access": False,
                    "volume": "medium",
                },
            },
            "version": "1.0.0",
            "owner_id": "placeholder",  # Will be overridden
            "tags": ["support", "customer-service", "demo"],
        }

        create_response = await client.post("/agents/", json=agent_data, headers=headers)
        await print_response(create_response)

        if create_response.status_code != 201:
            print("\n✗ Agent creation failed")
            return

        agent = create_response.json()
        agent_id = agent["id"]

        print(f"\n✓ Agent created successfully")
        print(f"  Agent ID: {agent_id}")
        print(f"  Risk Score: {agent['risk_score']}")
        print(f"  Status: {agent['status']}")

        # Step 3: Submit for approval
        await print_step("3", "Submit Agent for Approval")

        submit_response = await client.post(
            f"/agents/{agent_id}/submit-approval", headers=headers
        )
        await print_response(submit_response)

        print("\n✓ Agent submitted for approval")

        # Step 4: Approve agent (as admin)
        await print_step("4", "Approve Agent (Admin Action)")

        admin_login_response = await client.post(
            "/users/login", json={"email": "admin@demo.com", "password": "admin123"}
        )

        if admin_login_response.status_code != 200:
            print("\n✗ Admin authentication failed")
            return

        admin_token = admin_login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        approve_response = await client.post(
            f"/agents/{agent_id}/approve", headers=admin_headers
        )
        await print_response(approve_response)

        print("\n✓ Agent approved by admin")

        # Step 5: Deploy agent
        await print_step("5", "Deploy Agent to Staging Environment")

        deployment_data = {
            "agent_id": agent_id,
            "environment": "staging",
            "configuration": {"replicas": 1, "monitoring_enabled": True},
            "triggered_by_id": "placeholder",  # Will be overridden
        }

        deploy_response = await client.post(
            "/deployments/", json=deployment_data, headers=headers
        )
        await print_response(deploy_response)

        if deploy_response.status_code != 201:
            print("\n✗ Deployment creation failed")
            return

        deployment = deploy_response.json()
        deployment_id = deployment["id"]

        print(f"\n✓ Deployment initiated")
        print(f"  Deployment ID: {deployment_id}")
        print(f"  Workflow ID: {deployment['workflow_id']}")
        print(f"  Status: {deployment['status']}")

        # Step 6: Monitor deployment
        await print_step("6", "Monitor Deployment Status")

        print("Checking deployment status...")
        for i in range(5):
            await asyncio.sleep(2)
            status_response = await client.get(
                f"/deployments/{deployment_id}", headers=headers
            )

            if status_response.status_code == 200:
                status = status_response.json()
                print(f"  [{i+1}/5] Status: {status['status']}")

                if status["status"] in ["completed", "failed", "rolled_back"]:
                    break
            else:
                print(f"  [{i+1}/5] Failed to fetch status")

        await print_response(status_response)

        # Step 7: Rollback (optional demo)
        await print_step("7", "Rollback Deployment (Demo)")

        print("Simulating rollback scenario...")

        rollback_response = await client.post(
            f"/deployments/{deployment_id}/rollback", headers=admin_headers
        )
        await print_response(rollback_response)

        if rollback_response.status_code == 200:
            print("\n✓ Deployment rolled back successfully")
        else:
            print("\n⚠ Rollback request processed (check status)")

        # Summary
        print()
        print("=" * 70)
        print("DEMO COMPLETE")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  ✓ Agent created: {agent_id}")
        print(f"  ✓ Agent approved by admin")
        print(f"  ✓ Deployment initiated: {deployment_id}")
        print(f"  ✓ Full audit trail captured")
        print()
        print("Next steps:")
        print("  - View Temporal UI: http://localhost:8080")
        print("  - View API docs: http://localhost:8000/docs")
        print("  - Query audit logs via API")
        print()


if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Demo failed: {e}")
        import traceback

        traceback.print_exc()
