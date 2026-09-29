import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_and_login_citizen(client: AsyncClient):
    # Register Citizen
    reg_resp = await client.post("/api/v1/auth/register", json={
        "email": "test.citizen@example.com",
        "password": "Password@123",
        "full_name": "Test Citizen",
        "mobile": "9988776655"
    })
    assert reg_resp.status_code == 201
    assert reg_resp.json()["email"] == "test.citizen@example.com"

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "test.citizen@example.com",
        "password": "Password@123"
    })
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["user"]["role"] == "CITIZEN"

    # Refresh token test
    ref_resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": body["refresh_token"]
    })
    assert ref_resp.status_code == 200
    assert "access_token" in ref_resp.json()
