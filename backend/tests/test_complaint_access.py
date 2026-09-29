import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.grievance import Category
from seed import seed_data


@pytest.mark.asyncio
async def test_anonymous_complaint_requires_tracking_session(client: AsyncClient, db_session):
    await seed_data(db_session)
    category = (await db_session.execute(select(Category).where(Category.code == "WATER_SUPPLY"))).scalar_one()

    submitted = await client.post("/api/v1/complaints/submit-anonymous", json={
        "subject": "Water pipe leak",
        "description": "A municipal water pipe is leaking continuously near the main road.",
        "district_code": "IND",
        "location_address": "Main Road, Indore",
        "category_id": category.id,
        "priority": "HIGH",
    })
    assert submitted.status_code == 201
    complaint_no = submitted.json()["complaint_no"]

    assert (await client.get(f"/api/v1/complaints/{complaint_no}")).status_code == 401

    tracked = await client.post("/api/v1/complaints/track-anonymous", json={
        "complaint_no": complaint_no,
        "tracking_code": submitted.json()["tracking_code"],
    })
    assert tracked.status_code == 200
    headers = {"Authorization": f"Bearer {tracked.json()['access_token']}"}

    detail = await client.get(f"/api/v1/complaints/{complaint_no}", headers=headers)
    assert detail.status_code == 200
    message = await client.post(
        f"/api/v1/complaints/{detail.json()['id']}/messages",
        json={"message": "Please confirm the repair timeline."},
        headers=headers,
    )
    assert message.status_code == 200
    assert message.json()["messages"][-1]["sender_role"] == "ANONYMOUS"


@pytest.mark.asyncio
async def test_ai_preview_does_not_require_a_persisted_complaint(client: AsyncClient, db_session):
    await seed_data(db_session)
    response = await client.post("/api/v1/ai/recommend", json={
        "subject": "Road damage",
        "description": "There is a dangerous pothole on the main road.",
    })
    assert response.status_code == 200
    assert response.json()["suggested_priority"] == "MEDIUM"
