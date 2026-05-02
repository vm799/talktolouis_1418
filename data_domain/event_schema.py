"""Event schema for Talk to Louis.

MongoDB document structures and dataclasses for:
1. ScreeningSession - post-screening session metadata
2. AuditLogEntry - every event logged during a session
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class ScreeningSession:
    """Represents a patient screening session.
    
    Stored in MongoDB collection: screening_sessions
    """
    session_id: str  # UUID from LiveKit room
    user_id: str  # Anonymous alias (demo: "user_1")
    tenant_id: str  # Multi-tenant scoping (demo: "default")
    screening_grade: Optional[str]  # R0-R4 or None if not yet known
    screening_date: datetime  # When the screening happened (ISO 8601)
    created_at: datetime  # When this session started
    updated_at: datetime  # Last event timestamp
    
    def to_dict(self) -> dict:
        """Convert to dict for MongoDB insert."""
        return asdict(self)


@dataclass
class AuditLogEntry:
    """Represents a single event during a session.
    
    Stored in MongoDB collection: louis_audit_log
    Every turn, every red flag, every escalation is logged here.
    """
    session_id: str  # Link back to session
    user_id: str  # Scoped to user (for GDPR, privacy)
    tenant_id: str  # Scoped to tenant (Phase 2: multi-tenant)
    event_type: str  # "greeting" | "question" | "red_flag" | "escalation"
    user_input: Optional[str]  # What the patient said (None for system events like greeting)
    response_type: str  # "greeting" | "explanation" | "reassurance" | "escalation"
    red_flag_status: bool  # True if red flag detected
    escalation_status: bool  # True if escalated to NHS 111
    timestamp: datetime  # Event timestamp (UTC, ISO 8601)
    
    def to_dict(self) -> dict:
        """Convert to dict for MongoDB insert."""
        return asdict(self)


# MongoDB collection names (constants)
SCREENING_SESSIONS_COLLECTION = "screening_sessions"
AUDIT_LOG_COLLECTION = "louis_audit_log"

# Event type constants
EVENT_TYPE_SCREENING_COMPLETED = "screening_completed"
EVENT_TYPE_GREETING = "greeting"
EVENT_TYPE_QUESTION = "question"
EVENT_TYPE_RED_FLAG = "red_flag"
EVENT_TYPE_ESCALATION = "escalation"
EVENT_TYPE_TASK_PENDING = "task_pending"

# Response type constants
RESPONSE_TYPE_GREETING = "greeting"
RESPONSE_TYPE_EXPLANATION = "explanation"
RESPONSE_TYPE_REASSURANCE = "reassurance"
RESPONSE_TYPE_ESCALATION = "escalation"
RESPONSE_TYPE_TASK_ACKNOWLEDGED = "task_acknowledged"
