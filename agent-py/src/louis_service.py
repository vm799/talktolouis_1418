"""Talk to Louis service layer.

Core business logic orchestrator:
1. Greeting (first turn)
2. Assess user question (detect red flags, route to template)
3. Escalate (NHS 111 pathway)

All methods are async and log every event to MongoDB.
"""

import logging
from datetime import datetime, timezone
from typing import Tuple

from response_templates import get_template, TEMPLATE_METADATA
from louis.red_flag_detector import RedFlagDetector
from data_domain.mongo_event_repo import MongoEventRepository
from data_domain.event_schema import (
    AuditLogEntry,
    EVENT_TYPE_SCREENING_COMPLETED,
    EVENT_TYPE_GREETING,
    EVENT_TYPE_QUESTION,
    EVENT_TYPE_RED_FLAG,
    EVENT_TYPE_ESCALATION,
    EVENT_TYPE_TASK_PENDING,
    RESPONSE_TYPE_GREETING,
    RESPONSE_TYPE_EXPLANATION,
    RESPONSE_TYPE_REASSURANCE,
    RESPONSE_TYPE_ESCALATION,
    RESPONSE_TYPE_TASK_ACKNOWLEDGED,
)

logger = logging.getLogger("louis_service")


class LouisService:
    """Orchestrates the Talk to Louis voice interaction."""

    def __init__(self, mongo_repo: MongoEventRepository):
        """Initialize with MongoDB repository.
        
        Args:
            mongo_repo: MongoEventRepository instance (data access layer)
        """
        self.mongo_repo = mongo_repo
        self.red_flag_detector = RedFlagDetector()

    async def greeting(
        self, session_id: str, user_id: str, tenant_id: str = "default"
    ) -> Tuple[str, bool]:
        """First turn: greet patient post-screening.
        
        Args:
            session_id: LiveKit room ID
            user_id: Patient ID (anonymous alias for demo)
            tenant_id: Multi-tenant scoping (default: "default")
            
        Returns:
            Tuple of (response_text, should_escalate)
            - response_text: Safe, hard-coded greeting
            - should_escalate: False (greeting never escalates)
        """
        response = get_template("greeting")
        
        # Log event
        entry = AuditLogEntry(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            event_type=EVENT_TYPE_SCREENING_COMPLETED,
            user_input=None,  # System event, no user input
            response_type=RESPONSE_TYPE_GREETING,
            red_flag_status=False,
            escalation_status=False,
            timestamp=datetime.now(timezone.utc),
        )
        await self.mongo_repo.insert_event(entry)
        
        logger.info(f"Greeting sent: session={session_id}, user={user_id}")
        
        return response, False

    async def assess_question(
        self, session_id: str, user_id: str, user_input: str, tenant_id: str = "default"
    ) -> Tuple[str, bool]:
        """Assess user question, detect red flags, route to appropriate template.

        Args:
            session_id: LiveKit room ID
            user_id: Patient ID
            user_input: What the patient said
            tenant_id: Multi-tenant scoping

        Returns:
            Tuple of (response_text, should_escalate)
            - response_text: Either escalation (red flag) or safe explanation/reassurance
            - should_escalate: True if red flag detected, False otherwise
        """
        # DERIVE STATE FROM MONGODB FIRST (proves event sourcing)
        current_state = await self.mongo_repo.derive_state(user_id)

        # If already escalated, short-circuit immediately (state-aware)
        if current_state == "escalated":
            response = get_template("escalation")
            entry = AuditLogEntry(
                session_id=session_id,
                user_id=user_id,
                tenant_id=tenant_id,
                event_type=EVENT_TYPE_ESCALATION,
                user_input=user_input,
                response_type=RESPONSE_TYPE_ESCALATION,
                red_flag_status=True,
                escalation_status=True,
                timestamp=datetime.now(timezone.utc),
            )
            await self.mongo_repo.insert_event(entry)
            logger.info(f"State-based escalation (already escalated): session={session_id}, user={user_id}")
            return response, True

        # *** NON-NEGOTIABLE: CHECK RED FLAGS FIRST ***
        is_red_flag = self.red_flag_detector.check(user_input)
        
        if is_red_flag:
            # Red flag: immediate escalation
            response = get_template("escalation")
            response_type = RESPONSE_TYPE_ESCALATION
            event_type = EVENT_TYPE_RED_FLAG
            flag_detected = self.red_flag_detector.get_flag_type(user_input)
            logger.warning(
                f"🚨 RED FLAG ESCALATION: session={session_id}, "
                f"user={user_id}, flag={flag_detected}"
            )
        else:
            # No red flag: route based on question content
            user_input_lower = user_input.lower()

            # Check for pending tasks in current state events (coordination signal)
            try:
                recent_events = await self.mongo_repo.get_events_by_user_recent(user_id)
                if not isinstance(recent_events, list):
                    recent_events = []
            except Exception as e:
                logger.warning(f"Failed to fetch recent events for task check: {e}")
                recent_events = []
            has_pending_task = any(
                isinstance(e, dict) and e.get("event_type") == EVENT_TYPE_TASK_PENDING
                for e in recent_events
            )
            is_timeline_question = any(
                keyword in user_input_lower
                for keyword in ["when", "how long", "results"]
            )

            # Simple heuristic routing
            if any(
                keyword in user_input_lower
                for keyword in ["next", "what", "when", "how", "timeline", "results"]
            ):
                # Question about process/timeline → explanation
                response = get_template("explanation")
                event_type = EVENT_TYPE_QUESTION
                if has_pending_task and is_timeline_question:
                    # System acknowledges it knows about pending work
                    response_type = RESPONSE_TYPE_TASK_ACKNOWLEDGED
                    logger.info(
                        f"Question type: task_acknowledged (pending task; session={session_id})"
                    )
                else:
                    response_type = RESPONSE_TYPE_EXPLANATION
                    logger.info(f"Question type: explanation (session={session_id})")
            else:
                # Generic or anxiety question → reassurance
                response = get_template("reassurance")
                response_type = RESPONSE_TYPE_REASSURANCE
                event_type = EVENT_TYPE_QUESTION
                logger.info(f"Question type: reassurance (session={session_id})")
        
        # Log event
        entry = AuditLogEntry(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            event_type=event_type,
            user_input=user_input,
            response_type=response_type,
            red_flag_status=is_red_flag,
            escalation_status=is_red_flag,
            timestamp=datetime.now(timezone.utc),
        )
        await self.mongo_repo.insert_event(entry)
        
        return response, is_red_flag

    async def escalate(
        self, session_id: str, user_id: str, reason: str, tenant_id: str = "default"
    ) -> str:
        """Explicit escalation (called when red flag detected).
        
        Args:
            session_id: LiveKit room ID
            user_id: Patient ID
            reason: Why we're escalating (e.g., red-flag type)
            tenant_id: Multi-tenant scoping
            
        Returns:
            Escalation response text (safe, NHS 111 guidance)
        """
        response = get_template("escalation")

        # Log escalation event
        entry = AuditLogEntry(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            event_type=EVENT_TYPE_ESCALATION,
            user_input=reason,
            response_type=RESPONSE_TYPE_ESCALATION,
            red_flag_status=True,
            escalation_status=True,
            timestamp=datetime.now(timezone.utc),
        )
        await self.mongo_repo.insert_event(entry)

        # Log a task_pending event so coordination engine can track outstanding work
        # (the escalation creates a downstream task: specialist review).
        pending_entry = AuditLogEntry(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            event_type=EVENT_TYPE_TASK_PENDING,
            user_input="awaiting_specialist_review",
            response_type=RESPONSE_TYPE_ESCALATION,
            red_flag_status=True,
            escalation_status=True,
            timestamp=datetime.now(timezone.utc),
        )
        await self.mongo_repo.insert_event(pending_entry)

        logger.warning(
            f"🚨 ESCALATION TRIGGERED: session={session_id}, "
            f"user={user_id}, reason={reason}"
        )

        return response

    async def get_session_summary(self, session_id: str, user_id: str) -> dict:
        """Get summary of a session (for analytics/dashboard).
        
        Args:
            session_id: LiveKit room ID
            user_id: Patient ID
            
        Returns:
            Summary dict with event counts and escalation status
        """
        events = await self.mongo_repo.get_session_events(session_id, user_id)
        
        escalations = [e for e in events if e.get("escalation_status")]
        red_flags = [e for e in events if e.get("red_flag_status")]
        
        summary = {
            "session_id": session_id,
            "user_id": user_id,
            "total_events": len(events),
            "red_flags_detected": len(red_flags),
            "escalations": len(escalations),
            "was_escalated": len(escalations) > 0,
            "first_event_time": events[0]["timestamp"] if events else None,
            "last_event_time": events[-1]["timestamp"] if events else None,
        }
        
        logger.info(f"Session summary: {summary}")
        return summary
