import asyncio
import os
import sys
import logging
from pathlib import Path
import httpx
from httpx import ASGITransport
from sqlalchemy import select

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.grievance import Category

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_e2e_lifecycle")

CITIZEN_EMAIL = "citizen.demo@example.com"
CITIZEN_PWD = "CitizenPass123!"

ADMIN_EMAIL = "admin.bhopal@example.com"
ADMIN_PWD = "AdminPass123!"

OFFICER_EMAIL = "officer.bhopal.revenue@example.com"
OFFICER_PWD = "OfficerPass123!"


async def run_lifecycle_verification():
    logger.info("Initializing E2E Complaint Lifecycle Verification on Neon...")

    # Look up Category ID for "OTHER" and Officer User ID from DB
    async with AsyncSessionLocal() as session:
        cat_res = await session.execute(select(Category).where(Category.code == "OTHER"))
        other_cat = cat_res.scalar_one_or_none()
        if not other_cat:
            raise RuntimeError("Category 'OTHER' not found in database. Seed reference data first.")
        other_cat_id = other_cat.id

        off_res = await session.execute(select(User).where(User.email == OFFICER_EMAIL))
        officer_user = off_res.scalar_one_or_none()
        if not officer_user:
            raise RuntimeError(f"Officer '{OFFICER_EMAIL}' not found in database. Seed demo users first.")
        officer_user_id = str(officer_user.id)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:

        # Step 1: Citizen Login
        logger.info("Step 1: Logging in as Demo Citizen (%s)...", CITIZEN_EMAIL)
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": CITIZEN_EMAIL, "password": CITIZEN_PWD}
        )
        assert login_resp.status_code == 200, f"Citizen login failed: {login_resp.text}"
        citizen_token = login_resp.json()["access_token"]
        citizen_headers = {"Authorization": f"Bearer {citizen_token}"}
        logger.info("Step 1 Passed: Citizen authenticated successfully.")

        # Step 2: Citizen Submits Complaint
        logger.info("Step 2: Submitting grievance for district 'BHO' and category 'OTHER'...")
        submit_payload = {
            "subject": "Civic grievance regarding road drainage maintenance",
            "description": "Urgent civic maintenance required at Zone 1 Bhopal to clear drainage overflow.",
            "district_code": "BHO",
            "location_address": "MP Nagar Zone 1, Bhopal, Madhya Pradesh",
            "category_id": other_cat_id,
            "priority": "MEDIUM",
            "contact_email": CITIZEN_EMAIL,
            "contact_mobile": "9876543210"
        }
        submit_resp = await client.post(
            "/api/v1/complaints/submit",
            json=submit_payload,
            headers=citizen_headers
        )
        assert submit_resp.status_code in [200, 201], f"Complaint submission failed: {submit_resp.text}"
        complaint_data = submit_resp.json()
        complaint_id = complaint_data["id"]
        complaint_no = complaint_data["complaint_no"]
        status_after_submit = complaint_data["status"]
        logger.info(
            "Step 2 Passed: Complaint created -> ID: %s | No: %s | Status: %s",
            complaint_id, complaint_no, status_after_submit
        )
        assert status_after_submit == "SUBMITTED", f"Expected status SUBMITTED, got {status_after_submit}"

        # Step 3: District Admin Login
        logger.info("Step 3: Logging in as Bhopal District Admin (%s)...", ADMIN_EMAIL)
        admin_login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}
        )
        assert admin_login_resp.status_code == 200, f"Admin login failed: {admin_login_resp.text}"
        admin_token = admin_login_resp.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        logger.info("Step 3 Passed: District Admin authenticated successfully.")

        # Step 4: Admin Assigns Complaint to Officer
        logger.info("Step 4: Assigning complaint %s to Bhopal Officer (%s)...", complaint_no, officer_user_id)
        assign_resp = await client.post(
            f"/api/v1/district-admin/complaints/{complaint_id}/assign",
            json={
                "officer_id": officer_user_id,
                "remarks": "Assigned to Bhopal Revenue Officer for on-ground inspection and resolution."
            },
            headers=admin_headers
        )
        assert assign_resp.status_code == 200, f"Admin assign failed: {assign_resp.text}"
        assign_data = assign_resp.json()
        logger.info("Step 4 Passed: %s", assign_data.get("message"))

        # Step 5: Officer Login
        logger.info("Step 5: Logging in as Bhopal Revenue Officer (%s)...", OFFICER_EMAIL)
        officer_login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": OFFICER_EMAIL, "password": OFFICER_PWD}
        )
        assert officer_login_resp.status_code == 200, f"Officer login failed: {officer_login_resp.text}"
        officer_token = officer_login_resp.json()["access_token"]
        officer_headers = {"Authorization": f"Bearer {officer_token}"}
        logger.info("Step 5 Passed: Officer authenticated successfully.")

        # Step 6: Officer Checks Assigned Queue
        logger.info("Step 6: Officer fetching assigned complaints queue...")
        queue_resp = await client.get(
            "/api/v1/officer/assigned-complaints",
            headers=officer_headers
        )
        assert queue_resp.status_code == 200, f"Fetch queue failed: {queue_resp.text}"
        queue_items = queue_resp.json()
        matching_item = next((item for item in queue_items if item["id"] == complaint_id), None)
        assert matching_item is not None, f"Complaint {complaint_id} not found in officer assigned queue"
        assert matching_item["status"] == "ASSIGNED", f"Expected ASSIGNED in queue, got {matching_item['status']}"
        logger.info("Step 6 Passed: Complaint %s verified in officer assigned queue (status: %s).", complaint_no, matching_item["status"])

        # Step 7: Officer Starts Complaint
        logger.info("Step 7: Officer marking complaint %s as IN_PROGRESS...", complaint_no)
        start_resp = await client.post(
            f"/api/v1/officer/complaints/{complaint_id}/start",
            params={"remarks": "Field inspection scheduled and team dispatched."},
            headers=officer_headers
        )
        assert start_resp.status_code == 200, f"Officer start failed: {start_resp.text}"
        logger.info("Step 7 Passed: %s", start_resp.json()["message"])

        # Step 8: Officer Resolves Complaint
        logger.info("Step 8: Officer resolving complaint %s...", complaint_no)
        resolve_payload = {
            "resolution_summary": "Drainage cleared and debris removed from Zone 1 site. Normal water flow restored.",
            "remarks": "Redressal action completed in compliance with civic service norms."
        }
        resolve_resp = await client.post(
            f"/api/v1/officer/complaints/{complaint_id}/resolve",
            json=resolve_payload,
            headers=officer_headers
        )
        assert resolve_resp.status_code == 200, f"Officer resolve failed: {resolve_resp.text}"
        logger.info("Step 8 Passed: %s", resolve_resp.json()["message"])

        # Step 9: Citizen Verifies Resolution
        logger.info("Step 9: Citizen verifying grievance status in my-complaints...")
        my_complaints_resp = await client.get(
            "/api/v1/complaints/my-complaints",
            headers=citizen_headers
        )
        assert my_complaints_resp.status_code == 200, f"Fetch my-complaints failed: {my_complaints_resp.text}"
        my_list = my_complaints_resp.json()
        verified_item = next((c for c in my_list if c["id"] == complaint_id), None)
        assert verified_item is not None, f"Complaint {complaint_id} not found in citizen list"
        assert verified_item["status"] == "RESOLVED", f"Expected status RESOLVED, got {verified_item['status']}"

        # Fetch detailed complaint record
        detail_resp = await client.get(
            f"/api/v1/complaints/{complaint_id}",
            headers=citizen_headers
        )
        assert detail_resp.status_code == 200, f"Fetch detail failed: {detail_resp.text}"
        detail_data = detail_resp.json()
        assert detail_data["status"] == "RESOLVED"
        assert detail_data["resolution_summary"] == resolve_payload["resolution_summary"]

        logger.info(
            "Step 9 Passed: Citizen confirmed complaint %s status is RESOLVED with summary: '%s'",
            complaint_no, detail_data["resolution_summary"]
        )

    print("\n=======================================================")
    print("  E2E LIFECYCLE VERIFICATION COMPLETED SUCCESSFULLY!   ")
    print(f"  Complaint No   : {complaint_no}")
    print(f"  District Code  : BHO")
    print(f"  Final Status   : RESOLVED")
    print("  Milestones     : SUBMITTED -> ASSIGNED -> IN_PROGRESS -> RESOLVED")
    print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(run_lifecycle_verification())
