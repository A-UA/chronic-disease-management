import httpx
import asyncio
import json
import uuid

BASE_URL = "http://localhost:8000/api/v1"


async def run_test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("--- 1. Testing Registration ---")
        email = f"test_{uuid.uuid4().hex[:6]}@example.com"
        reg_data = {"email": email, "password": "testpassword123", "name": "Test User"}
        resp = await client.post(f"{BASE_URL}/auth/register", json=reg_data)
        if resp.status_code != 200:
            print(f"FAILED Registration: {resp.text}")
            return
        reg_json = resp.json()
        org_id = reg_json["org_id"]
        print(f"SUCCESS: User registered, Org ID: {org_id}")

        print("\n--- 2. Testing Login ---")
        login_data = {"username": email, "password": "testpassword123"}
        resp = await client.post(f"{BASE_URL}/auth/login/access-token", data=login_data)
        if resp.status_code != 200:
            print(f"FAILED Login: {resp.text}")
            return
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": str(org_id)}
        print("SUCCESS: Logged in and got token")

        print("\n--- 3. Testing KB Creation ---")
        kb_data = {"name": "Test KB", "description": "Testing RAG flow"}
        resp = await client.post(f"{BASE_URL}/kb/", json=kb_data, headers=headers)
        if resp.status_code != 200:
            print(f"FAILED KB Creation: {resp.text}")
            return
        kb_id = resp.json()["id"]
        print(f"SUCCESS: KB created, KB ID: {kb_id}")

        print("\n--- 4. Testing Document Upload ---")
        files = {
            "file": ("test.txt", b"This is a test document content about AI and RAG.")
        }
        resp = await client.post(
            f"{BASE_URL}/kb/{kb_id}/documents", files=files, headers=headers
        )
        if resp.status_code != 200:
            print(f"FAILED Doc Upload: {resp.text}")
            return
        doc_id = resp.json()["id"]
        print(f"SUCCESS: Document uploaded, ID: {doc_id}")

        print("\n--- 5. Testing Patient Profile ---")
        profile_data = {
            "real_name": "Test Patient",
            "gender": "male",
            "medical_history": {"condition": "Healthy"},
        }
        resp = await client.put(
            f"{BASE_URL}/biz/patients/me", json=profile_data, headers=headers
        )
        if resp.status_code != 200:
            print(f"FAILED Profile Update: {resp.text}")
            return
        patient_id = resp.json()["id"]
        print(f"SUCCESS: Patient profile created/updated, ID: {patient_id}")

        print("\n--- 6. Testing Family Linking ---")
        # Create a second user as family member
        family_email = f"family_{uuid.uuid4().hex[:6]}@example.com"
        await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": family_email,
                "password": "familypassword123",
                "name": "Family User",
            },
        )

        # Link family member
        link_data = {
            "patient_id": patient_id,
            "family_user_email": family_email,
            "relationship_type": "brother",
            "access_level": 1,
        }
        resp = await client.post(
            f"{BASE_URL}/biz/family/links", json=link_data, headers=headers
        )
        if resp.status_code != 200:
            print(f"FAILED Family Link: {resp.text}")
            return
        print(f"SUCCESS: Family link created for {family_email}")

        print("\n--- 7. Wait for Background Processing (2s) ---")
        await asyncio.sleep(2)

        print("\n--- 8. Testing Chat (SSE) ---")
        chat_data = {
            "kb_id": kb_id,
            "conversation_id": str(uuid.uuid4()),
            "query": "What is this document about?",
        }
        async with client.stream(
            "POST", f"{BASE_URL}/biz/chat", json=chat_data, headers=headers
        ) as response:
            if response.status_code != 200:
                print(f"FAILED Chat: {await response.aread()}")
                return

            print("Streaming Response:")
            async for line in response.aiter_lines():
                if line:
                    print(line)


if __name__ == "__main__":
    asyncio.run(run_test())
