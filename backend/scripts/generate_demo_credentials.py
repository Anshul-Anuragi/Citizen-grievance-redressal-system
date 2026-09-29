import asyncio
import os
import sys
import secrets
import string
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Ensure backend directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import (
    User, UserRole, DistrictAdminProfile, OfficerProfile,
    District, Department, Category, CategoryDepartmentMapping, SLARule, PriorityEnum, RefreshToken
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("credential_generator")

MP_DISTRICTS = [
    ("AGM", "Agar Malwa", "आगर मालवा"),
    ("ALI", "Alirajpur", "अलीराजपुर"),
    ("ANP", "Anuppur", "अनूपपुर"),
    ("ASH", "Ashoknagar", "अशोकनगर"),
    ("BAL", "Balaghat", "बालाघाट"),
    ("BAR", "Barwani", "बड़वानी"),
    ("BET", "Betul", "बैतूल"),
    ("BHI", "Bhind", "भिंड"),
    ("BHO", "Bhopal", "भोपाल"),
    ("BUR", "Burhanpur", "बुरहानपुर"),
    ("CHT", "Chhatarpur", "छतरपुर"),
    ("CHH", "Chhindwara", "छिंदवाड़ा"),
    ("DAM", "Damoh", "दमोह"),
    ("DAT", "Datia", "दतिया"),
    ("DEW", "Dewas", "देवास"),
    ("DHA", "Dhar", "धार"),
    ("DIN", "Dindori", "डिंडोरी"),
    ("GUN", "Guna", "गुना"),
    ("GWL", "Gwalior", "ग्वालियर"),
    ("HAR", "Harda", "हरदा"),
    ("HOS", "Narmadapuram", "नर्मदापुरम"),
    ("IND", "Indore", "इन्दौर"),
    ("JAB", "Jabalpur", "जबलपुर"),
    ("JHA", "Jhabua", "झाबुआ"),
    ("KAT", "Katni", "कटनी"),
    ("KHA", "Khandwa", "खंडवा"),
    ("KHR", "Khargone", "खरगोन"),
    ("MAN", "Mandla", "मंडला"),
    ("MDS", "Mandsaur", "मंदसौर"),
    ("MOR", "Morena", "मुरैना"),
    ("NAR", "Narsinghpur", "नरसिंहपुर"),
    ("NEE", "Neemuch", "नेमच"),
    ("NIW", "Niwari", "निवाड़ी"),
    ("PAN", "Panna", "पन्ना"),
    ("RAI", "Raisen", "रायसेन"),
    ("RAJ", "Rajgarh", "राजगढ़"),
    ("RAT", "Ratlam", "रतलाम"),
    ("REW", "Rewa", "रीवा"),
    ("SAG", "Sagar", "सागर"),
    ("SAT", "Satna", "सतना"),
    ("SEH", "Sehore", "सीहोर"),
    ("SEO", "Seoni", "सिवनी"),
    ("SHA", "Shahdol", "शहडोल"),
    ("SHJ", "Shajapur", "शाजापुर"),
    ("SHE", "Sheopur", "श्योपुर"),
    ("SHI", "Shivpuri", "शिवपुरी"),
    ("SID", "Sidhi", "सीधी"),
    ("SIN", "Singrauli", "सिंगरौली"),
    ("TIK", "Tikamgarh", "टीकमगढ़"),
    ("UJJ", "Ujjain", "उज्जैन"),
    ("UMA", "Umaria", "उमरिया"),
    ("VID", "Vidisha", "विदिशा"),
    ("MAU", "Mauganj", "मऊगंज"),
    ("MAI", "Maihar", "मैहर"),
    ("PND", "Pandhurna", "पांढुर्णा")
]

DEPARTMENTS = [
    ("PWD", "Public Works Department (PWD)", "लोक निर्माण विभाग"),
    ("MPPKVVCL", "Electricity Board (Discom)", "विद्युत वितरण कम्पनी"),
    ("NAGAR_NIGAM", "Urban Administration & Housing", "नगरीय विकास एवं आवास विभाग"),
    ("PHE", "Public Health Engineering (Water)", "लोक स्वास्थ्य यांत्रिकी विभाग"),
    ("SANITATION", "Waste Management & Sanitation", "स्वच्छता एवं अपशिष्ट प्रबंधन"),
    ("TRANSPORT", "Regional Transport Office (RTO)", "परिवहन विभाग"),
    ("REVENUE", "Revenue & Public Certificates", "राजस्व एवं लोक सेवा गारंटी"),
    ("IT_EGOV", "IT & MPOnline Governance", "इलेक्ट्रॉनिक्स एवं सुशासन (MPOnline)")
]

CATEGORIES = [
    ("WATER_SUPPLY", "Water Supply & Contamination", "पेयजल आपूर्ति एवं प्रदूषण", "PHE", 24.0),
    ("ELECTRICITY_POWER", "Electricity Outage & Transformer", "बिजली कटौती एवं ट्रांसफार्मर समस्या", "MPPKVVCL", 24.0),
    ("ROADS_POTHOLES", "Road Repair & Potholes", "सड़क मरम्मत एवं गड्ढे", "PWD", 48.0),
    ("DRAINAGE_SEWAGE", "Drainage & Sewage Overflow", "नाली एवं सीवरेज ओवरफ्लो", "NAGAR_NIGAM", 36.0),
    ("GARBAGE_WASTE", "Garbage Clearance & Waste Management", "कचरा उठान एवं अपशिष्ट प्रबंधन", "SANITATION", 24.0),
    ("STREET_LIGHTS", "Street Light Failure", "स्ट्रीट लाइट खराबी", "NAGAR_NIGAM", 24.0),
    ("OTHER", "Other Civic Grievance", "अन्य नागरिक शिकायत", "NAGAR_NIGAM", 72.0)
]

def generate_random_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*")
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)
    return "".join(password)

async def generate_and_seed_credentials(provided_session: Optional[AsyncSession] = None):
    if provided_session is None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    credentials_log = []
    credentials_log.append("# LOCAL DEVELOPMENT & DEMO CREDENTIALS REPORT\n")
    credentials_log.append(f"> **Generated On**: {datetime.now(timezone.utc).isoformat()}\n")
    credentials_log.append("> **SECURITY NOTICE**: This file contains local test credentials. It is added to `.gitignore` and must NEVER be committed to version control.\n\n")

    async def _run_seeding(session: AsyncSession):
        # 1. Bulk pre-fetch districts & departments
        existing_dists = {d.code: d for d in (await session.execute(select(District))).scalars().all()}
        for code, en, hi in MP_DISTRICTS:
            if code not in existing_dists:
                dist = District(code=code, name_en=en, name_hi=hi, is_active=True)
                session.add(dist)
                existing_dists[code] = dist

        existing_depts = {d.code: d for d in (await session.execute(select(Department))).scalars().all()}
        for code, en, hi in DEPARTMENTS:
            if code not in existing_depts:
                dept = Department(code=code, name_en=en, name_hi=hi, is_active=True)
                session.add(dept)
                await session.flush()
                existing_depts[code] = dept

        dept_map = {code: dept.id for code, dept in existing_depts.items()}

        # 2. Bulk pre-fetch categories
        existing_cats = {c.code: c for c in (await session.execute(select(Category))).scalars().all()}
        for cat_code, en, hi, dept_code, sla_hours in CATEGORIES:
            if cat_code not in existing_cats:
                cat = Category(code=cat_code, name_en=en, name_hi=hi, default_sla_hours=sla_hours, is_active=True)
                session.add(cat)
                await session.flush()
                existing_cats[cat_code] = cat

                dept_id = dept_map.get(dept_code)
                if dept_id:
                    session.add(CategoryDepartmentMapping(category_id=cat.id, department_id=dept_id, is_active=True))

                session.add(SLARule(category_id=cat.id, priority=PriorityEnum.HIGH, multiplier=0.5, resolution_deadline_hours=sla_hours * 0.5))
                session.add(SLARule(category_id=cat.id, priority=PriorityEnum.MEDIUM, multiplier=1.0, resolution_deadline_hours=sla_hours * 1.0))
                session.add(SLARule(category_id=cat.id, priority=PriorityEnum.LOW, multiplier=1.5, resolution_deadline_hours=sla_hours * 1.5))

        await session.flush()

        # Pre-fetch existing users & profiles into memory map to eliminate 1000s of SQL round-trips
        existing_users = {u.email.lower(): u for u in (await session.execute(select(User).options(selectinload(User.district_admin_profile), selectinload(User.officer_profile)))).scalars().all()}
        existing_officers_by_code = {op.officer_id: op for op in (await session.execute(select(OfficerProfile))).scalars().all()}
        existing_admins_by_dist = {dp.district_code: dp for dp in (await session.execute(select(DistrictAdminProfile))).scalars().all()}

        def provision_user_in_memory(email: str, name: str, role: UserRole, mobile: str = "9800000000"):
            email_clean = email.lower().strip()
            plain_pwd = generate_random_password(14)
            pwd_hash = get_password_hash(plain_pwd, rounds=4)

            user = existing_users.get(email_clean)
            if not user:
                user = User(
                    email=email_clean,
                    password_hash=pwd_hash,
                    full_name=name,
                    mobile=mobile,
                    role=role,
                    is_active=True,
                    is_verified=True
                )
                session.add(user)
                existing_users[email_clean] = user
            else:
                user.password_hash = pwd_hash
                user.is_active = True
                session.add(user)

            return user, plain_pwd

        # 4. Provision Citizen Demo Account
        cit_user, cit_pwd = provision_user_in_memory("citizen@example.com", "Rajesh Kumar Sharma", UserRole.CITIZEN)
        credentials_log.append("## 1. Citizen Account\n")
        credentials_log.append("| Role | Full Name | Email | Password |\n| --- | --- | --- | --- |\n")
        credentials_log.append(f"| Registered Citizen | {cit_user.full_name} | `{cit_user.email}` | `{cit_pwd}` |\n\n")

        # 5. Provision 55 District Admin Accounts
        credentials_log.append("## 2. District Admin Accounts (55 MP Districts)\n")
        credentials_log.append("| District Code | District Name | Email | Password |\n| --- | --- | --- | --- |\n")

        for code, name_en, _ in MP_DISTRICTS:
            admin_email = f"admin.{code.lower()}@mp.gov.in"
            admin_user, admin_pwd = provision_user_in_memory(admin_email, f"{name_en} Collectorate Admin", UserRole.DISTRICT_ADMIN)
            
            if admin_user.district_admin_profile:
                admin_user.district_admin_profile.district_code = code
            elif existing_admins_by_dist.get(code):
                admin_prof = existing_admins_by_dist[code]
                admin_prof.user_id = admin_user.id
                admin_user.district_admin_profile = admin_prof
            else:
                profile = DistrictAdminProfile(user_id=admin_user.id, district_code=code)
                admin_user.district_admin_profile = profile
                session.add(profile)
                existing_admins_by_dist[code] = profile

            credentials_log.append(f"| `{code}` | {name_en} | `{admin_email}` | `{admin_pwd}` |\n")

        credentials_log.append("\n")

        # 7. Provision 440 Officer Accounts (55 Districts x 8 Departments)
        credentials_log.append("## 4. Grievance Officer Accounts (55 Districts x 8 Departments = 440 Officers)\n")
        credentials_log.append("| Officer ID | District | Department | Email | Password |\n| --- | --- | --- | --- | --- |\n")

        for code, dist_en, _ in MP_DISTRICTS:
            seq = 1
            for dept_code, dept_en, _ in DEPARTMENTS:
                off_email = f"officer.{code.lower()}.{dept_code.lower()}@mp.gov.in"
                off_code = f"OFF-{code}-{seq:03d}"
                off_name = f"Er. Officer ({dept_code} {dist_en})"

                off_user, off_pwd = provision_user_in_memory(off_email, off_name, UserRole.OFFICER)

                if existing_officers_by_code.get(off_code):
                    off_prof = existing_officers_by_code[off_code]
                    off_prof.user_id = off_user.id
                    off_prof.district_code = code
                    off_prof.department_id = dept_map[dept_code]
                    off_prof.is_available = True
                    off_user.officer_profile = off_prof
                elif off_user.officer_profile:
                    off_prof = off_user.officer_profile
                    off_prof.officer_id = off_code
                    off_prof.district_code = code
                    off_prof.department_id = dept_map[dept_code]
                    off_prof.is_available = True
                    existing_officers_by_code[off_code] = off_prof
                else:
                    profile = OfficerProfile(
                        user_id=off_user.id,
                        officer_id=off_code,
                        district_code=code,
                        department_id=dept_map[dept_code],
                        is_available=True,
                        active_workload=0
                    )
                    off_user.officer_profile = profile
                    session.add(profile)
                    existing_officers_by_code[off_code] = profile

                credentials_log.append(f"| `{off_code}` | {dist_en} (`{code}`) | {dept_code} | `{off_email}` | `{off_pwd}` |\n")
                seq += 1

        # Single bulk commit for lightning fast completion
        await session.commit()

    if provided_session is not None:
        await _run_seeding(provided_session)
    else:
        async with AsyncSessionLocal() as session:
            await _run_seeding(session)

    # Save to local gitignored markdown file
    local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".local"))
    os.makedirs(local_dir, exist_ok=True)
    local_filepath = os.path.join(local_dir, "LOCAL_CREDENTIALS.md")

    content_str = "".join(credentials_log)
    with open(local_filepath, "w", encoding="utf-8") as f:
        f.write(content_str)

    admin_count = len(MP_DISTRICTS)
    officer_count = len(MP_DISTRICTS) * len(DEPARTMENTS)

    logger.info("Successfully generated credentials and seeded database:")
    logger.info(f" - Total Districts Seeded: {len(MP_DISTRICTS)}")
    logger.info(f" - Total Departments Seeded: {len(DEPARTMENTS)}")
    logger.info(f" - District Admin Accounts Provisioned: {admin_count}")
    logger.info(f" - Grievance Officer Accounts Provisioned: {officer_count}")
    logger.info(f" - Plaintext credentials exported strictly to local gitignored path: {local_filepath}")

if __name__ == "__main__":
    asyncio.run(generate_and_seed_credentials())
