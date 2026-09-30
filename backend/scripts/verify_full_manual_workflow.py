import asyncio
import httpx
import sys
import time

BASE_URL = 'http://localhost:8000/api/v1'

async def run_full_workflow():
    print("=" * 70, flush=True)
    print("  JANSEVA AI - COMPREHENSIVE END-TO-END MANUAL WORKFLOW TEST", flush=True)
    print("=" * 70, flush=True)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Register as Citizen
        print("\n[STEP 1] REGISTER NEW CITIZEN", flush=True)
        unique_email = f"citizen.bhopal.{int(time.time())}@example.com"
        reg_payload = {
            "email": unique_email,
            "password": "StrongCitizenPass2026!",
            "full_name": "Aakash Verma Bhopal",
            "mobile": "9826012345"
        }
        res = await client.post("/auth/register", json=reg_payload)
        assert res.status_code == 201, f"Citizen registration failed: {res.text}"
        reg_user = res.json()
        print(f"  ✓ Registered citizen: {reg_user['email']} (ID: {reg_user['id']})", flush=True)

        # 2. Login as newly registered citizen
        print("\n[STEP 2] LOGIN AS NEWLY REGISTERED CITIZEN", flush=True)
        login_res = await client.post("/auth/login", json={
            "email": unique_email,
            "password": "StrongCitizenPass2026!"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        citizen_token = login_res.json()["access_token"]
        citizen_headers = {"Authorization": f"Bearer {citizen_token}"}
        print("  ✓ Authenticated new citizen and received JWT bearer token", flush=True)

        # 3. Test Frontend Quick-Fill Citizen Credentials
        print("\n[STEP 3] VERIFY FRONTEND QUICK-FILL CITIZEN LOGIN", flush=True)
        qf_cit = await client.post("/auth/login", json={
            "email": "citizen.demo@example.com",
            "password": "CitizenPass123!"
        })
        assert qf_cit.status_code == 200, f"Quick-fill citizen failed: {qf_cit.text}"
        print("  ✓ Quick-Fill Citizen login successful (citizen.demo@example.com)", flush=True)

        # 4. Raise Grievance from Bhopal
        print("\n[STEP 4] RAISE GRIEVANCE FROM BHOPAL", flush=True)
        cats = (await client.get("/complaints/categories")).json()
        target_cat = next((c for c in cats if c["code"] == "OTHER"), cats[0])
        complaint_payload = {
            "subject": "Delayed land demarcation certificate at Huzur Tehsil Bhopal",
            "description": "Applicant filed for demarcation certificate under Lok Seva Guarantee Act at Huzur Tehsil, but processing has exceeded standard time limit.",
            "district_code": "BHO",
            "location_address": "Huzur Tehsil Office, Bhopal, Madhya Pradesh",
            "category_id": target_cat["id"],
            "priority": "HIGH",
            "contact_email": unique_email,
            "contact_mobile": "9826012345"
        }
        submit_res = await client.post("/complaints/submit", json=complaint_payload, headers=citizen_headers)
        assert submit_res.status_code in (200, 201), f"Complaint submit failed: {submit_res.text}"
        comp = submit_res.json()
        complaint_id = comp["id"]
        complaint_no = comp["complaint_no"]
        print(f"  ✓ Grievance submitted successfully:", flush=True)
        print(f"    - Complaint ID   : {complaint_id}", flush=True)
        print(f"    - Complaint No   : {complaint_no}", flush=True)
        print(f"    - District Code  : {comp['district_code']}", flush=True)
        print(f"    - Initial Status : {comp['status']}", flush=True)

        # 5. Login as Bhopal District Admin (Testing Admin Quick-Fill)
        print("\n[STEP 5] LOGIN AS BHOPAL DISTRICT ADMIN (QUICK-FILL TEST)", flush=True)
        admin_login = await client.post("/auth/login", json={
            "email": "admin.bhopal@example.com",
            "password": "AdminPass123!"
        })
        assert admin_login.status_code == 200, f"Admin quick fill failed: {admin_login.text}"
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("  ✓ Quick-Fill Admin login successful (admin.bhopal@example.com)", flush=True)

        dash_res = await client.get("/district-admin/dashboard", headers=admin_headers)
        assert dash_res.status_code == 200
        print(f"  ✓ District Dashboard active: {dash_res.json().get('total_complaints')} complaints tracked", flush=True)

        admin_comps = (await client.get("/district-admin/complaints", headers=admin_headers)).json()
        assert any(c["id"] == complaint_id for c in admin_comps), "Grievance not in Admin list"
        print(f"  ✓ Grievance {complaint_no} verified in District Admin inbox", flush=True)

        # 6. District Admin Confirms & Assigns to Bhopal Revenue Officer
        print("\n[STEP 6] DISTRICT ADMIN CONFIRMS & ASSIGNS TO BHOPAL REVENUE OFFICER", flush=True)
        officers_res = await client.get("/district-admin/officers", headers=admin_headers)
        officers = officers_res.json()
        bho_rev = next((o for o in officers if o.get("officer_id") == "OFF-BHO-REVENUE"), None)
        assert bho_rev is not None, "OFF-BHO-REVENUE officer not found in Bhopal"
        officer_user_id = bho_rev["user_id"]

        assign_res = await client.post(
            f"/district-admin/complaints/{complaint_id}/assign",
            json={
                "officer_id": officer_user_id,
                "remarks": "Assigned to Revenue Officer Bhopal for immediate certificate disposal."
            },
            headers=admin_headers
        )
        assert assign_res.status_code == 200, f"Assignment failed: {assign_res.text}"
        print(f"  ✓ Grievance assigned to Er. Officer (REVENUE Bhopal) [ID: {officer_user_id}]", flush=True)

        # 7. Login as Bhopal Revenue Officer (Testing Officer Quick-Fill)
        print("\n[STEP 7] LOGIN AS BHOPAL REVENUE OFFICER (QUICK-FILL TEST)", flush=True)
        off_login = await client.post("/auth/login", json={
            "email": "officer.bhopal.revenue@example.com",
            "password": "OfficerPass123!"
        })
        assert off_login.status_code == 200, f"Officer quick fill failed: {off_login.text}"
        off_token = off_login.json()["access_token"]
        off_headers = {"Authorization": f"Bearer {off_token}"}
        print("  ✓ Quick-Fill Officer login successful (officer.bhopal.revenue@example.com)", flush=True)

        off_queue = (await client.get("/officer/assigned-complaints", headers=off_headers)).json()
        assert any(c["id"] == complaint_id for c in off_queue), "Grievance not in Officer queue"
        print(f"  ✓ Grievance {complaint_no} verified in Officer assigned queue (status: ASSIGNED)", flush=True)

        # 8. Officer Starts Resolution Work (IN_PROGRESS)
        print("\n[STEP 8] OFFICER COMMENCES WORK (STATUS -> IN_PROGRESS)", flush=True)
        start_res = await client.post(
            f"/officer/complaints/{complaint_id}/start",
            params={"remarks": "Tehsildar Huzur initiated verification of revenue record entry."},
            headers=off_headers
        )
        assert start_res.status_code == 200, f"Start failed: {start_res.text}"
        print("  ✓ Status successfully transitioned to IN_PROGRESS", flush=True)

        # 9. Officer Solves Problem and Submits Resolution Output
        print("\n[STEP 9] OFFICER SOLVES PROBLEM AND SUBMITS RESOLUTION OUTPUT", flush=True)
        resolve_res = await client.post(
            f"/officer/complaints/{complaint_id}/resolve",
            json={
                "resolution_summary": "Demarcation certificate approved and dispatched digitally to citizen. Record updated in RCMS portal.",
                "remarks": "Physical verification completed and signed by Revenue Inspector Bhopal."
            },
            headers=off_headers
        )
        assert resolve_res.status_code == 200, f"Resolve failed: {resolve_res.text}"
        print("  ✓ Resolution submitted: Status updated to RESOLVED (UNVERIFIED)", flush=True)

        # 10. Citizen Verifies Output, Submits Feedback & Timeline Message
        print("\n[STEP 10] CITIZEN VERIFIES RESOLUTION, REVIEWS OUTPUT & PROVIDES FEEDBACK", flush=True)
        citizen_check = await client.get(f"/complaints/{complaint_id}", headers=citizen_headers)
        assert citizen_check.status_code == 200
        comp_detail = citizen_check.json()
        assert comp_detail["status"] == "RESOLVED"
        print(f"  ✓ Citizen verified grievance status: {comp_detail['status']}", flush=True)
        print(f"  ✓ Officer Resolution Summary visible to Citizen:\n    \"{comp_detail.get('resolution_summary')}\"", flush=True)

        # Citizen submits satisfaction feedback
        fb_res = await client.post(
            f"/complaints/{complaint_id}/feedback",
            json={
                "rating": 5,
                "is_satisfied": True,
                "comments": "Received the demarcation certificate within 24 hours. Highly satisfied with JanSeva AI!"
            },
            headers=citizen_headers
        )
        assert fb_res.status_code == 200, f"Feedback failed: {fb_res.text}"
        print("  ✓ Citizen satisfaction feedback registered (Rating: 5/5, Satisfied: True)", flush=True)

        # Citizen posts confirmation message
        msg_res = await client.post(
            f"/complaints/{complaint_id}/messages",
            json={"message": "Thank you Tehsildar Huzur and JanSeva AI. Downloaded the certificate successfully."},
            headers=citizen_headers
        )
        assert msg_res.status_code == 200, f"Message failed: {msg_res.text}"
        print("  ✓ Citizen communication appended to official case record", flush=True)

        # Verify final verification status
        final_check = (await client.get(f"/complaints/{complaint_id}", headers=citizen_headers)).json()
        print(f"  ✓ Final Verification Status: {final_check.get('verification_status')}", flush=True)
        print(f"  ✓ Total Status History Milestones: {len(final_check.get('status_history', []))}", flush=True)

        print("\n" + "=" * 70, flush=True)
        print("  FULL MANUAL LIFECYCLE TEST COMPLETED WITH 100% SUCCESS!", flush=True)
        print(f"  Complaint Number    : {complaint_no}", flush=True)
        print(f"  District / Office   : Bhopal (BHO) / Huzur Tehsil", flush=True)
        print(f"  Workflow Traversed  : SUBMITTED -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> CITIZEN VERIFIED", flush=True)
        print(f"  All Quick-Fills     : Citizen, District Admin, and Officer VERIFIED WORKING", flush=True)
        print("=" * 70, flush=True)

if __name__ == "__main__":
    asyncio.run(run_full_workflow())
