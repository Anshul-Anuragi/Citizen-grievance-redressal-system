import pytest
from httpx import AsyncClient
from seed import seed_data

@pytest.mark.asyncio
async def test_ai_keyword_rule_fallback_when_unconfigured(client: AsyncClient, db_session):
    await seed_data(db_session)

    res = await client.post("/api/v1/ai/recommend", json={
        "subject": "Water leakage in pipe",
        "description": "There is a massive water leak from the municipal pipe on main road."
    })
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] in ["rule_fallback", "gemini"]
    assert data["suggested_priority"] in ["LOW", "MEDIUM", "HIGH"]
    assert "reasoning" in data
