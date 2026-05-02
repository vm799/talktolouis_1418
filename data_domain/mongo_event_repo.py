"""MongoDB event repository for Talk to Louis.

Data access layer for inserting and querying screening sessions + audit logs.
All operations are scoped by user_id and tenant_id for privacy/multi-tenancy.

Usage:
    db = await get_db()  # From starter repo db/client.py
    repo = MongoEventRepository(db)
    await repo.insert_event(entry)
"""

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError
from data_domain.event_schema import (
    ScreeningSession,
    AuditLogEntry,
    SCREENING_SESSIONS_COLLECTION,
    AUDIT_LOG_COLLECTION,
)
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger("mongo_event_repo")


class MongoEventRepository:
    """Data access layer for Talk to Louis events."""

    def __init__(self, db: AsyncDatabase):
        """Initialize with MongoDB database.
        
        Args:
            db: Async MongoDB database instance (from pymongo 4.0+)
        """
        self.db = db

    async def insert_event(self, entry: AuditLogEntry) -> str:
        """Insert a single audit log entry.
        
        Args:
            entry: AuditLogEntry dataclass
            
        Returns:
            Inserted document ID (string)
            
        Raises:
            Exception: If MongoDB insert fails
        """
        try:
            collection = self.db[AUDIT_LOG_COLLECTION]
            result = await collection.insert_one(entry.to_dict())
            logger.info(f"Event logged: {entry.event_type} ({result.inserted_id})")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to insert event: {e}")
            raise

    async def get_session_events(
        self, session_id: str, user_id: str
    ) -> List[dict]:
        """Get all events for a session (scoped by user_id).
        
        Args:
            session_id: LiveKit room ID
            user_id: Patient ID (for scoping)
            
        Returns:
            List of audit log entries (dicts), ordered by timestamp
        """
        try:
            collection = self.db[AUDIT_LOG_COLLECTION]
            query = {"session_id": session_id, "user_id": user_id}
            cursor = await collection.find(query).sort("timestamp", 1)
            events = await cursor.to_list(length=1000)
            logger.info(f"Retrieved {len(events)} events for session {session_id}")
            return events
        except Exception as e:
            logger.error(f"Failed to get session events: {e}")
            return []

    async def get_user_sessions(self, user_id: str, limit: int = 10) -> List[dict]:
        """Get all sessions for a user (for analytics).
        
        Args:
            user_id: Patient ID
            limit: Max sessions to return
            
        Returns:
            List of screening sessions (dicts), ordered by created_at descending
        """
        try:
            collection = self.db[SCREENING_SESSIONS_COLLECTION]
            cursor = await collection.find({"user_id": user_id}).sort("created_at", -1)
            sessions = await cursor.to_list(length=limit)
            logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
            return sessions
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []

    async def insert_session(self, session: ScreeningSession) -> str:
        """Insert a screening session.
        
        Args:
            session: ScreeningSession dataclass
            
        Returns:
            Inserted document ID (string)
        """
        try:
            collection = self.db[SCREENING_SESSIONS_COLLECTION]
            result = await collection.insert_one(session.to_dict())
            logger.info(f"Session created: {session.session_id} ({result.inserted_id})")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to insert session: {e}")
            raise

    async def update_session(
        self, session_id: str, user_id: str, updates: dict
    ) -> bool:
        """Update a session (e.g., set screening_grade).
        
        Args:
            session_id: LiveKit room ID
            user_id: Patient ID (for scoping)
            updates: Dict of fields to update (e.g., {"screening_grade": "R2"})
            
        Returns:
            True if matched + updated, False if not found
        """
        try:
            collection = self.db[SCREENING_SESSIONS_COLLECTION]
            query = {"session_id": session_id, "user_id": user_id}
            result = await collection.update_one(query, {"$set": updates})
            updated = result.matched_count > 0
            logger.info(f"Session {session_id} updated: {updated}")
            return updated
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            return False

    async def count_red_flags(self, user_id: str) -> int:
        """Count red-flag events for a user (for analytics).
        
        Args:
            user_id: Patient ID
            
        Returns:
            Number of red-flag events
        """
        try:
            collection = self.db[AUDIT_LOG_COLLECTION]
            count = await collection.count_documents(
                {"user_id": user_id, "red_flag_status": True}
            )
            return count
        except Exception as e:
            logger.error(f"Failed to count red flags: {e}")
            return 0

    async def get_escalation_events(self, user_id: str) -> List[dict]:
        """Get all escalation events for a user.

        Args:
            user_id: Patient ID

        Returns:
            List of escalation events (dicts)
        """
        try:
            collection = self.db[AUDIT_LOG_COLLECTION]
            cursor = await collection.find(
                {"user_id": user_id, "escalation_status": True}
            ).sort("timestamp", -1)
            events = await cursor.to_list(length=1000)
            return events
        except Exception as e:
            logger.error(f"Failed to get escalation events: {e}")
            return []

    async def get_events_by_user_recent(
        self, user_id: str, hours: int = 4
    ) -> List[dict]:
        """Get all events for a user in the last N hours (for state reconstruction).

        Args:
            user_id: Patient ID
            hours: Look back window (default 4 hours)

        Returns:
            List of events sorted by timestamp ascending
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        try:
            collection = self.db[AUDIT_LOG_COLLECTION]
            cursor = await collection.find(
                {"user_id": user_id, "timestamp": {"$gte": cutoff}}
            ).sort("timestamp", 1)
            return await cursor.to_list(length=500)
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []

    async def derive_state(self, user_id: str, hours: int = 4) -> str:
        """Reconstruct current system state by replaying recent events.

        States: 'waiting_post_screening' | 'post_screening' | 'escalated'

        Args:
            user_id: Patient ID
            hours: Look back window for event history

        Returns:
            State string derived from event history
        """
        events = await self.get_events_by_user_recent(user_id, hours)
        state = "waiting_post_screening"
        for event in events:
            if event.get("event_type") == "screening_completed":
                state = "post_screening"
            if event.get("event_type") in ("red_flag", "escalation"):
                state = "escalated"
        logger.info(f"State derived for user {user_id}: {state} (from {len(events)} events)")
        return state
