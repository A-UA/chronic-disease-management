import httpx
import asyncio
import uuid
import pytest
from app.main import app
from app.db.session import AsyncSessionLocal
from app.db.models import PatientManagerAssignment

BASE_URL = "http://testserver/api/v1"


@pytest.mark.asyncio
async def test_manager_workflow():
    # Use ASGITransport to test without a running server
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=BASE_URL
    ) as client:
        # 1. Register Manager
        manager_email = f"manager_{uuid.uuid4().hex[:6]}@example.com"
        resp = await client.post(
            "/auth/register",
            json={"email": manager_email, "password": "pass", "name": "Manager One"},
        )
        assert resp.status_code == 200
        data = resp.json()
        org_id = data["org_id"]
        manager_id = data["id"]

        # Login Manager
        resp = await client.post(
            "/auth/login/access-token",
            data={"username": manager_email, "password": "pass"},
        )
        assert resp.status_code == 200
        manager_token = resp.json()["access_token"]
        manager_headers = {
            "Authorization": f"Bearer {manager_token}",
            "X-Organization-Id": str(org_id),
        }

        # 2. Create PatientProfile for testing
        profile_data = {"real_name": "Test Patient", "gender": "male"}
        resp = await client.put(
            "/patients/me", json=profile_data, headers=manager_headers
        )
        assert resp.status_code == 200
        patient_id = resp.json()["id"]
        resp = await client.get("/patients/me", headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == str(patient_id)

        # 3. Create assignment in DB directly
        async with AsyncSessionLocal() as db:
            assignment = PatientManagerAssignment(
                org_id=int(org_id),
                manager_id=int(manager_id),
                patient_id=int(patient_id),
            )
            db.add(assignment)
            await db.commit()

        # 4. Test GET /managers/my-patients
        resp = await client.get("/managers/my-patients", headers=manager_headers)
        assert resp.status_code == 200
        patients = resp.json()
        assert len(patients) > 0
        assert patients[0]["id"] == str(patient_id)

        # 5. Test POST /managers/patients/{id}/suggestions
        suggest_data = {"content": "Drink more water.", "suggestion_type": "lifestyle"}
        resp = await client.post(
            f"/managers/patients/{patient_id}/suggestions",
            json=suggest_data,
            headers=manager_headers,
        )
        assert resp.status_code == 200

        # 6. Test GET /managers/patients/{id}/suggestions
        resp = await client.get(
            f"/managers/patients/{patient_id}/suggestions", headers=manager_headers
        )
        assert resp.status_code == 200
        suggestions = resp.json()
        assert len(suggestions) > 0
        assert suggestions[0]["content"] == "Drink more water."
