import httpx
import asyncio
import uuid
import pytest

BASE_URL = "http://localhost:8000/api/v1"

@pytest.mark.asyncio
async def test_manager_workflow():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Register Manager
        manager_email = f"manager_{uuid.uuid4().hex[:6]}@example.com"
        resp = await client.post(f"{BASE_URL}/auth/register", json={
            "email": manager_email, "password": "pass", "name": "Manager One"
        })
        org_id = resp.json()["org_id"]
        
        # Login Manager
        resp = await client.post(f"{BASE_URL}/auth/login/access-token", data={"username": manager_email, "password": "pass"})
        manager_token = resp.json()["access_token"]
        manager_headers = {"Authorization": f"Bearer {manager_token}", "X-Organization-Id": str(org_id)}

        # 2. Register Patient
        patient_email = f"patient_{uuid.uuid4().hex[:6]}@example.com"
        await client.post(f"{BASE_URL}/auth/register", json={
            "email": patient_email, "password": "pass", "name": "Patient One"
        })
        # Note: In our current logic, register creates a NEW org for each user.
        # To test assignment, we need them in the SAME org.
        # For simplicity in this test, we'll use the DB directly to create an assignment in the manager's org.
        # But we want to test APIs. So let's assume the manager adds the patient to their org.
        # Currently, we don't have an "add user to org" API implemented for external users easily.
        
        # Let's create a PatientProfile for the MANAGER themselves (as a shortcut for test)
        # OR we can implement a quick hack in a test utility if needed.
        # Actually, let's create a PatientProfile for the manager to test the "list" API.
        
        profile_data = {"real_name": "Test Patient", "gender": "male"}
        resp = await client.put(f"{BASE_URL}/patients/me", json=profile_data, headers=manager_headers)
        patient_id = resp.json()["id"]
        manager_id = resp.json()["user_id"]

        # 3. Manually create assignment in DB (since we don't have an admin API for this yet)
        # We'll use a hidden/internal test endpoint or just trust the logic if we can't easily touch DB here.
        # Wait, I have run_shell_command. I can use a python script to touch the DB.
        
        setup_script = f"""
from app.db.session import AsyncSessionLocal
from app.db.models import PatientManagerAssignment
import asyncio
from uuid import UUID

async def setup():
    async with AsyncSessionLocal() as db:
        assignment = PatientManagerAssignment(
            org_id=UUID('{org_id}'),
            manager_id=UUID('{manager_id}'),
            patient_id=UUID('{patient_id}')
        )
        db.add(assignment)
        await db.commit()

asyncio.run(setup())
"""
        with open("temp_setup.py", "w") as f:
            f.write(setup_script)
        
        import os
        os.system("uv run python temp_setup.py")
        os.remove("temp_setup.py")

        # 4. Test GET /managers/patients
        resp = await client.get(f"{BASE_URL}/managers/patients", headers=manager_headers)
        assert resp.status_code == 200
        patients = resp.json()
        assert len(patients) > 0
        assert patients[0]["id"] == patient_id
        print("SUCCESS: Manager saw assigned patient")

        # 5. Test POST /managers/patients/{id}/suggestions
        suggest_data = {"content": "Drink more water.", "suggestion_type": "lifestyle"}
        resp = await client.post(f"{BASE_URL}/managers/patients/{patient_id}/suggestions", json=suggest_data, headers=manager_headers)
        assert resp.status_code == 200
        print("SUCCESS: Manager created suggestion")

        # 6. Test GET /managers/patients/{id}/suggestions
        resp = await client.get(f"{BASE_URL}/managers/patients/{patient_id}/suggestions", headers=manager_headers)
        assert resp.status_code == 200
        suggestions = resp.json()
        assert len(suggestions) > 0
        assert suggestions[0]["content"] == "Drink more water."
        print("SUCCESS: Manager viewed suggestion history")

if __name__ == "__main__":
    asyncio.run(test_manager_workflow())
