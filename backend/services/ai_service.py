"""
SentinelOps AI - AI Incident Intelligence Service.
Integrates Member 2's IncidentIntelligencePipeline with the persistent SaaS database.
Detects 3-layer anomalies, correlates alerts into incidents, identifies root causes,
and produces actionable recommendations without duplicate incident spam.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

# Ensure sentinelops-ai is importable for Member 2's AI modules
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
AI_DIR = ROOT_DIR / "sentinelops-ai"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai import IncidentIntelligencePipeline
from backend.db.models import Incident as DBIncident, AuditLog
from backend.db.models import utc_now


class BackendAIService:
    """
    Manages the lifecycle of AI analysis for incoming telemetry payloads.
    Translates Member 2 AI pipeline results into persistent multi-tenant incidents.
    """

    def __init__(self):
        self.pipeline = IncidentIntelligencePipeline()

    def process_telemetry_for_tenant(
        self,
        payload_dict: Dict[str, Any],
        organization_id: str,
        db: Session,
    ) -> Tuple[List[Any], Optional[DBIncident]]:
        """
        Runs the 3-layer anomaly detection, alert correlation, root cause analysis,
        and recommendation generation on incoming telemetry for an organization.
        Creates or updates persistent DBIncident records with deduplication.
        """
        # Ensure tenant_id in payload matches the target organization
        analysis_payload = dict(payload_dict)
        analysis_payload["tenant_id"] = organization_id

        # 1. Run Member 2's Incident Intelligence Pipeline
        try:
            alerts_generated, correlated_incidents = self.pipeline.process_telemetry(analysis_payload)
        except Exception as e:
            # Fallback gracefully if AI model raises unexpected exception
            return [], None

        if not correlated_incidents:
            return alerts_generated, None

        # 2. Process correlated incidents into persistent database
        active_db_incident: Optional[DBIncident] = None

        for ai_inc in correlated_incidents:
            source_id = ai_inc.affected_source
            now = utc_now()

            # Format comprehensive description with root cause, evidence, and recommendations
            desc_lines = []
            if ai_inc.root_cause_hint:
                desc_lines.append(f"Root Cause Hypothesis: {ai_inc.root_cause_hint}")
            if ai_inc.evidence_summary:
                desc_lines.append("Evidence Observations:")
                for ev in ai_inc.evidence_summary:
                    desc_lines.append(f"  • {ev}")
            if ai_inc.recommendations:
                desc_lines.append("Actionable Recommendations:")
                for rec in ai_inc.recommendations:
                    desc_lines.append(f"  [{rec.priority}] {rec.action}: {rec.description}")

            formatted_description = "\n".join(desc_lines) if desc_lines else "AI correlated incident."

            # Check for existing active incident on this source to prevent duplicate records
            existing_incident = db.execute(
                select(DBIncident).where(
                    and_(
                        DBIncident.organization_id == organization_id,
                        DBIncident.source_id == source_id,
                        DBIncident.status.in_(["open", "investigating"]),
                    )
                )
            ).scalar_one_or_none()

            if existing_incident:
                # Deduplication: Update ongoing incident
                existing_incident.last_updated_at = now
                existing_incident.description = formatted_description
                # Escalate severity if incoming severity is higher
                if ai_inc.severity == "CRITICAL" and existing_incident.severity != "CRITICAL":
                    existing_incident.severity = "CRITICAL"
                active_db_incident = existing_incident
            else:
                # Create brand new incident
                new_incident = DBIncident(
                    id=ai_inc.id,
                    organization_id=organization_id,
                    title=ai_inc.title,
                    description=formatted_description,
                    severity=ai_inc.severity,
                    status="open",
                    source_id=source_id,
                    first_detected_at=now,
                    last_updated_at=now,
                )
                db.add(new_incident)

                # Record Audit Log for Incident Creation
                audit = AuditLog(
                    organization_id=organization_id,
                    action="incident.detected_by_ai",
                    resource_type="incident",
                    resource_id=new_incident.id,
                    safe_metadata={
                        "title": new_incident.title,
                        "severity": new_incident.severity,
                        "source_id": source_id,
                    },
                )
                db.add(audit)
                active_db_incident = new_incident

        try:
            db.commit()
            if active_db_incident:
                db.refresh(active_db_incident)
        except Exception:
            db.rollback()

        return alerts_generated, active_db_incident


# Global AI Service Singleton
ai_service = BackendAIService()
