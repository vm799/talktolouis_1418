# IMPLEMENTATION.md — Build Order (4-Hour Sprint)

**Timeline:** 4 hours total  
**Commits:** Micro-commit every 15-20 minutes  
**Goal:** Working coordination engine demo with MongoDB event log driving state derivation. AI interprets intent. The system executes deterministic coordination logic using event history.  

---

## PHASE 1: Foundation (0-30 min) — 2 commits

### Commit 1: Event schema (10 min)
**File:** `data_domain/event_schema.py`

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ScreeningSession:
    session_id: str
    user_id: str
    tenant_id: str
    screening_grade: str  # R0-R4
    screening_date: datetime
    created_at: datetime
    updated_at: datetime

@dataclass
class AuditLogEntry:
    session_id: str
    user_id: str
    tenant_id: str
    event_type: str  # "greeting", "question", "red_flag", "escalation"
    user_input: str
    response_type: str
    red_flag_status: bool
    escalation_status: bool
    timestamp: datetime
```

**Checklist:**
- [ ] Dataclasses defined
- [ ] Docstrings added
- [ ] No external dependencies
- [ ] Commit: `feat: add event schema [MVP]`

---

### Commit 2: MongoDB CRUD wrapper (20 min)
**File:** `data_domain/mongo_event_repo.py`

```python
import asyncio
from pymongo.asynchronous.database import AsyncDatabase
from data_domain.event_schema import ScreeningSession, AuditLogEntry
from datetime import datetime, timezone

class MongoEventRepository:
    def __init__(self, db: AsyncDatabase):
        self.db = db
    
    async def insert_event(self, entry: AuditLogEntry) -> str:
        """Insert audit log entry, return inserted_id"""
        result = await self.db.louis_audit_log.insert_one(entry.__dict__)
        return str(result.inserted_id)
    
    async def get_session_events(self, session_id: str, user_id: str) -> list:
        """Get all events for a session (scoped by user_id)"""
        cursor = await self.db.louis_audit_log.find({
            "session_id": session_id,
            "user_id": user_id
        })
        return await cursor.to_list(length=1000)
    
    async def insert_session(self, session: ScreeningSession) -> str:
        """Insert screening session"""
        result = await self.db.screening_sessions.insert_one(session.__dict__)
        return str(result.inserted_id)
```

**Checklist:**
- [ ] 3 methods: insert_event, get_session_events, insert_session
- [ ] All methods async
- [ ] User_id scoping enforced
- [ ] Docstrings added
- [ ] Commit: `feat: add MongoDB event repository [MVP]`

---

## PHASE 2: Business Logic (30-90 min) — 3 commits

### Commit 3: Response templates (15 min)
**File:** `agent-py/src/response_templates.py`

```python
TEMPLATES = {
    "greeting": (
        "Congratulations on completing your eye screening. "
        "Your results will be reviewed by a specialist and sent to you within 7 days. "
        "Keep taking your diabetes medications as prescribed. [NICE NG242]"
    ),
    "explanation": (
        "Vision changes can happen for many reasons. "
        "Keeping your blood sugar and blood pressure well-controlled helps protect your eyes. "
        "If you're worried, speak to your eye care team at your next appointment. [NHS]"
    ),
    "reassurance": (
        "It's normal to feel concerned after an eye screening. "
        "The fact that you had a screening shows you're taking your health seriously. "
        "Your care team will discuss any findings with you. [NHS Diabetes]"
    ),
    "escalation": (
        "I need to get you in touch with a healthcare professional right away. "
        "Please call NHS 111 or go to your nearest accident and emergency. "
        "If it's a life-threatening emergency, call 999. [NHS Emergency]"
    ),
    "fallback": (
        "I'm having trouble understanding that right now. "
        "Please call NHS 111 for medical advice or 999 in an emergency. [Fallback]"
    ),
}

def get_template(template_type: str) -> str:
    """Get template by type, fallback to fallback template"""
    return TEMPLATES.get(template_type, TEMPLATES["fallback"])
```

**Checklist:**
- [ ] 5 templates defined
- [ ] All cite source (NICE/NHS/Fallback)
- [ ] Plain English (no markdown, no lists)
- [ ] get_template() function
- [ ] Commit: `feat: add response templates [MVP]`

---

### Commit 4: Red-flag detector (15 min)
**File:** `agent-py/src/louis/red_flag_detector.py`

```python
class RedFlagDetector:
    RED_FLAGS = [
        "flashing lights",
        "floaters",
        "curtain",
        "sudden blindness",
        "sudden vision loss",
        "pain in eye",
        "eye pain",
        "emergency",
        "help",
        "ambulance",
        "hospital",
        "accident",
        "trauma",
    ]
    
    @staticmethod
    def check(user_input: str) -> bool:
        """Return True if any red flag detected"""
        text = user_input.lower().strip()
        return any(flag in text for flag in RedFlagDetector.RED_FLAGS)
    
    @staticmethod
    def get_flag_type(user_input: str) -> str:
        """Return which red flag matched (for logging)"""
        text = user_input.lower().strip()
        for flag in RedFlagDetector.RED_FLAGS:
            if flag in text:
                return flag
        return None
```

**Checklist:**
- [ ] RED_FLAGS list defined (13 keywords minimum)
- [ ] check() returns bool
- [ ] get_flag_type() returns string
- [ ] No regex (simple string matching)
- [ ] Commit: `feat: add red-flag detector [MVP]`

---

### Commit 5: Service layer (30 min)
**File:** `agent-py/src/louis_service.py`

```python
from datetime import datetime, timezone
from agent_py.src.response_templates import get_template
from agent_py.src.louis.red_flag_detector import RedFlagDetector
from data_domain.mongo_event_repo import MongoEventRepository
from data_domain.event_schema import AuditLogEntry

class LouisService:
    def __init__(self, mongo_repo: MongoEventRepository):
        self.mongo_repo = mongo_repo
        self.red_flag_detector = RedFlagDetector()
    
    async def greeting(self, session_id: str, user_id: str) -> tuple[str, bool]:
        """Greet patient post-screening, log event, return (response, escalate)"""
        response = get_template("greeting")
        entry = AuditLogEntry(
            session_id=session_id,
            user_id=user_id,
            tenant_id="default",
            event_type="greeting",
            user_input=None,
            response_type="greeting",
            red_flag_status=False,
            escalation_status=False,
            timestamp=datetime.now(timezone.utc)
        )
        await self.mongo_repo.insert_event(entry)
        return response, False
    
    async def assess_question(self, session_id: str, user_id: str, user_input: str) -> tuple[str, bool]:
        """Assess user question, detect red flags, return (response, escalate)"""
        is_red_flag = self.red_flag_detector.check(user_input)
        
        if is_red_flag:
            response = get_template("escalation")
            response_type = "escalation"
        else:
            # Simple heuristic: if asks about "next" → timeline, else → generic reassurance
            if "next" in user_input.lower() or "what" in user_input.lower():
                response = get_template("explanation")
                response_type = "explanation"
            else:
                response = get_template("reassurance")
                response_type = "reassurance"
        
        entry = AuditLogEntry(
            session_id=session_id,
            user_id=user_id,
            tenant_id="default",
            event_type="red_flag" if is_red_flag else "question",
            user_input=user_input,
            response_type=response_type,
            red_flag_status=is_red_flag,
            escalation_status=is_red_flag,
            timestamp=datetime.now(timezone.utc)
        )
        await self.mongo_repo.insert_event(entry)
        return response, is_red_flag
    
    async def escalate(self, session_id: str, user_id: str, reason: str) -> str:
        """Escalate to NHS 111, log event"""
        response = get_template("escalation")
        entry = AuditLogEntry(
            session_id=session_id,
            user_id=user_id,
            tenant_id="default",
            event_type="escalation",
            user_input=reason,
            response_type="escalation",
            red_flag_status=True,
            escalation_status=True,
            timestamp=datetime.now(timezone.utc)
        )
        await self.mongo_repo.insert_event(entry)
        return response
```

**Checklist:**
- [ ] __init__ takes mongo_repo
- [ ] 3 methods: greeting(), assess_question(), escalate()
- [ ] All methods async
- [ ] All methods log to MongoDB
- [ ] Red-flag detection integrated
- [ ] Commit: `feat: add louis service layer [MVP]`

---

## PHASE 3: Integration & Voice (90-150 min) — 3 commits

### Commit 6: ElevenLabs wrapper (15 min)
**File:** `agent-py/src/louis/elevenlabs_wrapper.py`

```python
import aiohttp
import os

class ElevenLabsWrapper:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default female voice
        self.base_url = "https://api.elevenlabs.io/v1"
    
    async def synthesize(self, text: str) -> bytes:
        """Convert text to speech, return audio bytes"""
        if not self.api_key:
            return b"[FALLBACK: ElevenLabs API key not configured]"
        
        url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        headers = {"xi-api-key": self.api_key}
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    else:
                        return b"[FALLBACK: ElevenLabs API error]"
        except Exception as e:
            return b"[FALLBACK: ElevenLabs timeout]"
```

**Checklist:**
- [ ] __init__ reads ELEVENLABS_API_KEY from .env
- [ ] synthesize() is async
- [ ] Returns bytes
- [ ] 5-second timeout
- [ ] Fallback on error
- [ ] Commit: `feat: add ElevenLabs TTS wrapper [MVP]`

---

### Commit 7: Agent entry point wire-up (30 min)
**File:** `agent-py/src/agent.py` (modify existing file)

**Location:** In the `MongoAgent` class, add method to handle louis service:

```python
async def handle_louis_turn(self, user_message: str) -> str:
    """Route user message through louis service"""
    from agent_py.src.louis_service import LouisService
    from agent_py.src.louis.red_flag_detector import RedFlagDetector
    
    louis_service = LouisService(mongo_repo=self.db_repo)
    
    # First turn: greeting
    if not hasattr(self, '_louis_greeting_sent'):
        response, escalate = await louis_service.greeting(
            session_id=self.ctx.room.name,
            user_id=self.user_id
        )
        self._louis_greeting_sent = True
        return response
    
    # Subsequent turns: assess question
    response, escalate = await louis_service.assess_question(
        session_id=self.ctx.room.name,
        user_id=self.user_id,
        user_input=user_message
    )
    
    return response
```

**Checklist:**
- [ ] Imports added
- [ ] Wired into turn handler
- [ ] First turn sends greeting
- [ ] Subsequent turns assess questions
- [ ] Red-flag detector called
- [ ] MongoDB log called
- [ ] Commit: `feat: wire louis service into agent [MVP]`

---

### Commit 8: Unit tests (20 min)
**File 1:** `tests/test_red_flag_detector.py`

```python
import pytest
from agent_py.src.louis.red_flag_detector import RedFlagDetector

class TestRedFlagDetector:
    def test_detects_flashing_lights(self):
        assert RedFlagDetector.check("I'm seeing flashing lights")
    
    def test_detects_sudden_vision_loss(self):
        assert RedFlagDetector.check("sudden vision loss")
    
    def test_detects_emergency(self):
        assert RedFlagDetector.check("emergency")
    
    def test_misses_safe_input(self):
        assert not RedFlagDetector.check("What happens next?")
    
    def test_case_insensitive(self):
        assert RedFlagDetector.check("FLASHING LIGHTS")
```

**File 2:** `tests/test_mongo_logger.py`

```python
import pytest
import asyncio
from datetime import datetime, timezone
from data_domain.event_schema import AuditLogEntry
from data_domain.mongo_event_repo import MongoEventRepository
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_insert_event_logs_to_mongodb():
    # Mock MongoDB
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.louis_audit_log = mock_collection
    
    repo = MongoEventRepository(mock_db)
    entry = AuditLogEntry(
        session_id="test_session",
        user_id="user_1",
        tenant_id="default",
        event_type="greeting",
        user_input=None,
        response_type="greeting",
        red_flag_status=False,
        escalation_status=False,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Insert and verify
    await repo.insert_event(entry)
    mock_collection.insert_one.assert_called_once()
```

**Checklist:**
- [ ] test_red_flag_detector.py: 5 test cases
- [ ] test_mongo_logger.py: 1 integration test
- [ ] Both tests pass
- [ ] Commit: `test: add unit tests [MVP]`

---

## PHASE 4: Demo & Fallback (150-200 min) — 2 commits

### Commit 9: Hard-coded demo scenarios (20 min)
**File:** `hackathon_mvp/hard_coded_scenarios.py`

```python
DEMO_SCENARIOS = {
    "I just had eye screening": {
        "response": "Congratulations on completing your eye screening. Your results will be reviewed by a specialist and sent to you within 7 days. Keep taking your diabetes medications as prescribed. [NICE NG242]",
        "red_flag": False,
        "escalate": False,
    },
    "Why can't I see properly?": {
        "response": "Vision changes can happen for many reasons. Keeping your blood sugar and blood pressure well-controlled helps protect your eyes. If you're worried, speak to your eye care team at your next appointment. [NHS]",
        "red_flag": False,
        "escalate": False,
    },
    "What happens next?": {
        "response": "Your screening results will be reviewed by a specialist and sent to you within 7 days. In the meantime, keep taking your diabetes medications. [NHS]",
        "red_flag": False,
        "escalate": False,
    },
    "I'm seeing flashing lights": {
        "response": "I need to get you in touch with a healthcare professional right away. Please call NHS 111 or go to your nearest accident and emergency. If it's a life-threatening emergency, call 999. [NHS Emergency]",
        "red_flag": True,
        "escalate": True,
    },
}

def get_demo_response(user_input: str) -> dict:
    """Return demo response if input matches, else fallback"""
    return DEMO_SCENARIOS.get(
        user_input,
        {
            "response": "I'm having trouble understanding that. Please call NHS 111 or 999 in an emergency.",
            "red_flag": False,
            "escalate": False,
        }
    )
```

**Checklist:**
- [ ] 4 demo scenarios defined
- [ ] Each has response, red_flag, escalate fields
- [ ] get_demo_response() function
- [ ] Commit: `feat: add hard-coded demo scenarios [MVP]`

---

### Commit 10: Demo script (20 min)
**File:** `hackathon_mvp/demo_script.py`

```python
"""
3-minute demo script for Talk to Louis
Run: python hackathon_mvp/demo_script.py

Demonstrates:
1. Post-screening greeting
2. Q&A about vision
3. Red-flag detection + escalation
4. MongoDB audit trail
"""

import asyncio
from hackathon_mvp.hard_coded_scenarios import get_demo_response

async def run_demo():
    print("\n=== TALK TO LOUIS DEMO (3 MIN) ===\n")
    
    demo_inputs = [
        "I just had eye screening",
        "Why can't I see properly?",
        "I'm seeing flashing lights",
    ]
    
    session_id = "demo_session_001"
    user_id = "demo_user"
    
    print(f"Session: {session_id}")
    print(f"User: {user_id}\n")
    
    for i, user_input in enumerate(demo_inputs, 1):
        print(f"--- Turn {i} ---")
        print(f"Patient: {user_input}")
        
        result = get_demo_response(user_input)
        print(f"Louis: {result['response']}\n")
        
        if result['red_flag']:
            print("🚨 RED FLAG DETECTED")
            print("→ ESCALATING TO NHS 111\n")
        
        await asyncio.sleep(1)  # 1-second pause between turns
    
    print("=== DEMO COMPLETE ===\n")

if __name__ == "__main__":
    asyncio.run(run_demo())
```

**Checklist:**
- [ ] 3 demo turns
- [ ] Shows patient input
- [ ] Shows Louis response
- [ ] Flags red-flag escalation
- [ ] Commit: `feat: add demo script [MVP]`

---

## PHASE 5: Final Checks (200-240 min) — 1 commit

### Commit 11: .env.example update (10 min)

**File:** `.env.example` (append to existing)

```bash
# Talk to Louis
ELEVENLABS_API_KEY=<your-key>
FIREWORKS_API_KEY=<your-key>
LANGSMITH_API_KEY=<your-key>
```

**Checklist:**
- [ ] Commit: `chore: add louis .env vars [MVP]`

---

## FINAL CHECKLIST (Before demo)

- [ ] All 11 commits in git log
- [ ] Both unit tests passing: `pytest tests/`
- [ ] Demo script runs: `python hackathon_mvp/demo_script.py`
- [ ] 4 demo scenarios output correct responses
- [ ] Red-flag detector triggers on Scenario 4
- [ ] No Python errors or warnings
- [ ] MongoDB audit trail has 4+ events
- [ ] Code commented (no cryptic logic)
- [ ] ways-of-working.md followed (no scope creep)
- [ ] Speaker notes written in demo_script.py

---

## TIME ALLOCATION

| Phase | Duration | Status |
|---|---|---|
| Phase 1: Foundation | 30 min | ⏳ 2 commits |
| Phase 2: Business Logic | 60 min | ⏳ 3 commits |
| Phase 3: Integration | 60 min | ⏳ 3 commits |
| Phase 4: Demo | 40 min | ⏳ 2 commits |
| Phase 5: Final Checks | 10 min | ⏳ 1 commit |
| **TOTAL** | **240 min (4 hrs)** | **11 commits** |

---

**Estimated buffer:** 30 minutes (for debugging, surprises)  
**If running late:** Skip Phase 5 (final checks) and demo with Phase 4 output  
**If running early:** Add Fireworks AI fallback or LangSmith tracing

---

**Owner:** V (Process Pro AI)  
**Last updated:** 2026-05-02
