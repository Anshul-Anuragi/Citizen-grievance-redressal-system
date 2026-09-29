import json
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.grievance import Category, Department, PriorityEnum
from app.models.ai import AIRecommendation, AIInsight

logger = logging.getLogger(__name__)

# Keyword Mapping Rule Engine Fallback
KEYWORD_MAPPINGS = {
    "water": ("WATER_SUPPLY", PriorityEnum.HIGH, "Issue pertains to public water supply, pipe leaks, or clean drinking water distribution."),
    "water supply": ("WATER_SUPPLY", PriorityEnum.HIGH, "Issue pertains to municipal water supply."),
    "pipe": ("WATER_SUPPLY", PriorityEnum.MEDIUM, "Issue involves pipeline repair or water leaks."),
    "electricity": ("ELECTRICITY_POWER", PriorityEnum.HIGH, "Electricity or power outage issue requiring urgent attention."),
    "power": ("ELECTRICITY_POWER", PriorityEnum.HIGH, "Power grid or transformer issue."),
    "transformer": ("ELECTRICITY_POWER", PriorityEnum.HIGH, "Dangerous transformer fault or high voltage hazard."),
    "road": ("ROADS_POTHOLES", PriorityEnum.MEDIUM, "Road damage, potholes, or civic infrastructure repair."),
    "pothole": ("ROADS_POTHOLES", PriorityEnum.MEDIUM, "Road safety hazard due to potholes."),
    "sewage": ("DRAINAGE_SEWAGE", PriorityEnum.HIGH, "Public health concern regarding sewage blockage."),
    "drainage": ("DRAINAGE_SEWAGE", PriorityEnum.MEDIUM, "Drain overflow or stormwater blockage."),
    "garbage": ("GARBAGE_WASTE", PriorityEnum.MEDIUM, "Solid waste accumulation or uncollected trash."),
    "trash": ("GARBAGE_WASTE", PriorityEnum.LOW, "Sanitation and waste clearance request."),
    "light": ("STREET_LIGHTS", PriorityEnum.LOW, "Street light replacement or dark alley lighting."),
    "street light": ("STREET_LIGHTS", PriorityEnum.LOW, "Defective street lighting."),
    "bus": ("PUBLIC_TRANSPORT", PriorityEnum.MEDIUM, "Public transport or city bus service inquiry/issue."),
    "transport": ("PUBLIC_TRANSPORT", PriorityEnum.MEDIUM, "Transit network complaint."),
    "certificate": ("APPLICATION_CERTIFICATE", PriorityEnum.MEDIUM, "Delayed issuance of civic certificate or official document."),
    "mponline": ("MPONLINE_KIOSK", PriorityEnum.MEDIUM, "Kiosk transaction or digital service issue."),
    "kiosk": ("MPONLINE_KIOSK", PriorityEnum.MEDIUM, "MPOnline kiosk service discrepancy."),
    "payment": ("PAYMENT_TRANSACTION", PriorityEnum.HIGH, "Failed online payment or billing refund request."),
}

class AIService:
    @staticmethod
    async def recommend_category_and_priority(
        db: AsyncSession,
        complaint_id: Optional[str],
        description: str,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates category, department & priority suggestions.
        Uses Gemini API if configured; falls back gracefully to Keyword Rule Engine if unavailable.
        Stores output in `ai_recommendations` when it belongs to a persisted complaint.
        Preview requests intentionally have no complaint ID and must not create an
        orphan record that violates the foreign-key constraint.
        """
        full_text = f"{subject or ''} {description}".lower()
        
        provider = "rule_fallback"
        model_used = "keyword-rule-engine-v1"
        suggested_category_code = "OTHER"
        suggested_priority = PriorityEnum.MEDIUM
        confidence = 0.65
        reasoning = "Rule-based analysis based on complaint description keywords."

        # 1. Try Gemini API if API Key is configured
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                
                prompt = f"""
You are an expert Indian Civic Grievance Classification System for Madhya Pradesh Government (MPOnline).
Analyze the following citizen complaint and recommend the appropriate Category and Priority.

Categories available:
- WATER_SUPPLY (Water Supply, Pipe Leak, Contamination)
- ELECTRICITY_POWER (Power Cut, Transformer, Voltage, Wire)
- ROADS_POTHOLES (Potholes, Road Repair, Asphalt)
- DRAINAGE_SEWAGE (Sewage Overflow, Drain Blockage)
- GARBAGE_WASTE (Uncollected Trash, Waste Accumulation)
- STREET_LIGHTS (Street Light Fuse, Dark Area)
- PUBLIC_SANITATION (Public Toilet, Hygiene)
- PUBLIC_TRANSPORT (City Bus, Transport Issues)
- PAYMENT_TRANSACTION (Failed Fee Payment, Portal Refund)
- MPONLINE_KIOSK (MPOnline Kiosk Overcharging, Service Delay)
- APPLICATION_CERTIFICATE (Income/Caste Certificate Delay)
- TECHNICAL_ISSUE (Portal Bug, Login Issue)
- GOVERNMENT_SERVICE (General Civic Service)
- DOCUMENT_VERIFICATION (Verification Delay)
- OTHER (General Grievance)

Priorities: LOW, MEDIUM, HIGH

Complaint Details:
Subject: {subject or 'N/A'}
Description: {description}

Respond strictly in valid JSON format:
{{
    "suggested_category_code": "CATEGORY_CODE",
    "suggested_priority": "LOW|MEDIUM|HIGH",
    "confidence": 0.85,
    "reasoning": "Brief explanation of recommendation"
}}
"""
                response = client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt
                )
                
                text_content = response.text.strip()
                if "```json" in text_content:
                    text_content = text_content.split("```json")[1].split("```")[0].strip()
                elif "```" in text_content:
                    text_content = text_content.split("```")[1].split("```")[0].strip()
                    
                ai_json = json.loads(text_content)
                suggested_category_code = ai_json.get("suggested_category_code", "OTHER")
                suggested_priority_str = ai_json.get("suggested_priority", "MEDIUM").upper()
                if suggested_priority_str in [p.value for p in PriorityEnum]:
                    suggested_priority = PriorityEnum(suggested_priority_str)
                confidence = float(ai_json.get("confidence", 0.90))
                reasoning = ai_json.get("reasoning", "Gemini AI automated recommendation.")
                provider = "gemini"
                model_used = settings.GEMINI_MODEL
                
            except Exception as e:
                logger.warning(f"Gemini API unavailable/failed ({e}). Falling back to rule engine.")

        # 2. Rule Engine Fallback if Gemini not used or failed
        if provider == "rule_fallback":
            matched = False
            for keyword, (cat_code, prio, reason) in KEYWORD_MAPPINGS.items():
                if keyword in full_text:
                    suggested_category_code = cat_code
                    suggested_priority = prio
                    reasoning = f"Keyword match found for '{keyword}': {reason}"
                    confidence = 0.80
                    matched = True
                    break
            if not matched:
                suggested_category_code = "OTHER"
                suggested_priority = PriorityEnum.MEDIUM
                confidence = 0.50
                reasoning = "Default rule-based classification."

        # Fetch Category DB object
        cat_result = await db.execute(
            select(Category).where(Category.code == suggested_category_code)
        )
        category_obj = cat_result.scalar_one_or_none()

        department_id = None
        if category_obj:
            # Query category department mapping
            from app.models.grievance import CategoryDepartmentMapping
            mapping_res = await db.execute(
                select(CategoryDepartmentMapping)
                .where(CategoryDepartmentMapping.category_id == category_obj.id, CategoryDepartmentMapping.is_active == True)
            )
            mapping = mapping_res.scalar_one_or_none()
            if mapping:
                department_id = mapping.department_id

        # Save AI Recommendation record (stored separately from administrative decision)
        if complaint_id:
            recommendation = AIRecommendation(
                complaint_id=complaint_id,
                suggested_category_id=category_obj.id if category_obj else None,
                suggested_department_id=department_id,
                suggested_priority=suggested_priority.value if isinstance(suggested_priority, PriorityEnum) else str(suggested_priority),
                confidence=confidence,
                reasoning=reasoning,
                provider=provider,
                model=model_used
            )
            db.add(recommendation)
            await db.commit()

        return {
            "suggested_category_id": category_obj.id if category_obj else None,
            "suggested_category_name": category_obj.name_en if category_obj else "Other",
            "suggested_department_id": department_id,
            "suggested_priority": suggested_priority.value if isinstance(suggested_priority, PriorityEnum) else str(suggested_priority),
            "confidence": confidence,
            "reasoning": reasoning,
            "provider": provider,
            "model": model_used
        }

    @staticmethod
    async def generate_admin_insights(
        db: AsyncSession,
        district_code: str,
        total_complaints: int,
        overdue_count: int,
        resolved_count: int,
        top_categories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generates operational insights for District Admin.
        Falls back to rule-based summary if Gemini API is unavailable.
        """
        summary = f"District {district_code} processed {total_complaints} total complaints with {resolved_count} resolutions and {overdue_count} overdue cases."
        highlights = [
            f"Resolution Rate: {round((resolved_count / total_complaints * 100), 1) if total_complaints > 0 else 0}%",
            f"Overdue Workload: {overdue_count} complaints require immediate intervention."
        ]
        recurring_themes = [f"Top active domain: {top_categories[0]['name'] if top_categories else 'General Civic Services'}"]
        suggestions = ["Prioritize overdue complaints and optimize officer workload distribution across departments."]
        provider = "rule_fallback"

        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                prompt = f"""
You are an executive administrative advisor for District {district_code} Grievance Operations.
Synthesize the following operational data into 3 strategic bullet points and 2 operational suggestions.

Data Summary:
- Total Complaints: {total_complaints}
- Resolved: {resolved_count}
- Overdue: {overdue_count}
- Category Breakdown: {json.dumps(top_categories[:5])}

Respond in valid JSON format:
{{
    "summary_text": "Executive summary paragraph",
    "highlights": ["Highlight 1", "Highlight 2"],
    "recurring_themes": ["Theme 1"],
    "operational_suggestions": ["Suggestion 1", "Suggestion 2"]
}}
"""
                resp = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
                text_content = resp.text.strip()
                if "```json" in text_content:
                    text_content = text_content.split("```json")[1].split("```")[0].strip()
                ai_json = json.loads(text_content)
                summary = ai_json.get("summary_text", summary)
                highlights = ai_json.get("highlights", highlights)
                recurring_themes = ai_json.get("recurring_themes", recurring_themes)
                suggestions = ai_json.get("operational_suggestions", suggestions)
                provider = "gemini"
            except Exception as e:
                logger.warning(f"Gemini Admin Insights fallback ({e})")

        # Save insight record
        insight_record = AIInsight(
            district_code=district_code,
            insight_type="DISTRICT_EXECUTIVE_SUMMARY",
            summary_text=summary,
            payload=json.dumps({"highlights": highlights, "suggestions": suggestions}),
            provider=provider
        )
        db.add(insight_record)
        await db.commit()

        return {
            "insight_type": "DISTRICT_EXECUTIVE_SUMMARY",
            "summary_text": summary,
            "highlights": highlights,
            "recurring_themes": recurring_themes,
            "operational_suggestions": suggestions,
            "provider": provider,
            "created_at": insight_record.created_at
        }
