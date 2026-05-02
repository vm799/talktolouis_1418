# talk_to_louis_context.md — Optimal Context for Code Generation

**Size:** 900 tokens | **Read time:** 3 minutes | **Use:** Before every code-generation prompt

---

## PART 1: System Prompt (300 tokens)

You are Claude Code, building a 4-hour MVP for "Talk to Louis" — a voice-first diabetic eye screening companion.

**Constraints (non-negotiable):**
- Do NOT diagnose or predict blindness
- Do NOT provide emergency advice (escalate to NHS 111)
- Do NOT remove MongoDB Atlas (audit trail mandatory)
- Do NOT add frameworks outside the starter repo (LangGraph, LangChain OK; NVIDIA, DeepAgents NO)
- Do NOT build full EHR or NHS integration (Phase 2 only)
- Do NOT invent architecture (reuse LiveKit starter patterns)

**When uncertain:** Reread `.claude/ways-of-working.md` (gotchas) or `.claude/CLAUDE.md` (routing)

**Decision tree:** "Is this in the 4 demo scenarios? → Is it in the starter repo? → Is it required for red-flag or audit? → If NO to all, delete from scope."

**Tone:** Brutally honest. Say "You are NOT building..." when scope creeps.

---

## PART 2: Event Schema (150 tokens)

MongoDB collections:

```python
# Collection: screening_sessions
{
  "session_id": str,              # UUID from LiveKit room
  "user_id": str,                 # Anonymous alias (demo: "user_1")
  "tenant_id": str,               # Demo only: "default"
  "screening_grade": str,         # R0/R1/R2/R3/R4 (demo: hardcoded)
  "screening_date": datetime,     # When screening happened
  "created_at": datetime,         # Session start
  "updated_at": datetime,         # Last event
}

# Collection: louis_audit_log
{
  "session_id": str,              # Link to session
  "user_id": str,                 # Scoped to user
  "tenant_id": str,               # Scoped to tenant
  "event_type": str,              # "greeting" | "question" | "red_flag" | "escalation"
  "user_input": str,              # What user said (nullable for system events)
  "response_type": str,           # "reassurance" | "explanation" | "escalation"
  "red_flag_status": bool,        # True if red flag detected
  "escalation_status": bool,      # True if escalated to human
  "timestamp": datetime,          # Event timestamp (UTC)
}
```

**CRUD in `data_domain/mongo_event_repo.py`:**
- `insert_event(session_id, user_id, event_type, user_input, response_type, red_flag, escalation)`
- `get_session(session_id)` → list of events
- `get_user_sessions(user_id)` → all sessions for user (analytics)

---

## PART 3: Four-Part Output Template (200 tokens)

All responses must follow this pattern (hard-coded, no LLM variation):

```python
TEMPLATES = {
    # Scenario 1: Post-screening greeting
    "greeting": """
Congratulations on completing your eye screening. 
Your screening results will be reviewed by a specialist and sent to you within 7 days.
In the meantime, keep taking your diabetes medications as prescribed.
[NICE NG242]
""",
    
    # Scenario 2: Safe explanation (generic)
    "explanation": """
Vision changes can happen for many reasons.
Keeping your blood sugar and blood pressure well-controlled helps protect your eyes.
If you're worried, speak to your eye care team at your next appointment.
[NHS England Eye Screening Standards]
""",
    
    # Scenario 3: Reassurance (anxiety)
    "reassurance": """
It's normal to feel concerned after an eye screening.
The fact that you had a screening shows you're taking your health seriously.
Your care team will discuss any findings with you directly.
[NHS Diabetes Care]
""",
    
    # Scenario 4: Escalation (red flag detected)
    "escalation": """
I need to get you in touch with a healthcare professional right away.
Please call NHS 111 or go to your nearest accident and emergency department.
If it's an emergency, call 999.
[NHS England Emergency Pathways]
""",
    
    # Fallback (if Fireworks API times out)
    "fallback": """
I'm having trouble understanding that right now.
Please call NHS 111 for immediate medical advice or 999 in an emergency.
[Fallback Safety Protocol]
""",
}
```

**Format:**
1. **What I see:** Observation (no diagnosis)
2. **What it means:** Plain English explanation (NICE-cited)
3. **What to do:** Action (appointment, monitor, escalate)
4. **Citations:** Always tag with `[NICE]` or `[NHS]`

---

## PART 4: Red-Flag Keyword List (50 tokens)

If ANY of these appear in user input → STOP normal flow → ESCALATE IMMEDIATELY.

```python
RED_FLAGS = [
    "flashing lights", "floaters", "curtain",
    "sudden blindness", "sudden vision loss",
    "pain in eye", "eye pain",
    "emergency", "help", "ambulance", "hospital",
    "accident", "trauma",
]
```

**Logic:**
```python
if any(keyword in user_input.lower() for keyword in RED_FLAGS):
    return TEMPLATES["escalation"]  # Hard-coded, no negotiation
```

---

## PART 5: Demo Scenarios (200 tokens)

The MVP must handle these 4 scenarios (hard-coded fallback if Fireworks fails):

### Scenario 1: Post-screening greeting
**User:** "I just had eye screening."  
**Response:** TEMPLATES["greeting"] (Congratulations...)  
**MongoDB log:** event_type="greeting", red_flag_status=False

### Scenario 2: Generic question
**User:** "Why can't I see properly?"  
**Response:** TEMPLATES["explanation"] (Vision changes can...)  
**MongoDB log:** event_type="question", response_type="explanation"

### Scenario 3: Reassurance
**User:** "What happens next?"  
**Response:** TEMPLATES["reassurance"] (It's normal to feel...) OR Provide timeline  
**MongoDB log:** event_type="reassurance"

### Scenario 4: Red-flag escalation
**User:** "I'm seeing flashing lights."  
**Response:** TEMPLATES["escalation"] (I need to get you...) + call NHS 111  
**MongoDB log:** event_type="red_flag", red_flag_status=True, escalation_status=True

---

## Implementation Checklist

- [ ] Event schema defined in `data_domain/event_schema.py`
- [ ] MongoDB repo CRUD in `data_domain/mongo_event_repo.py`
- [ ] Service logic in `agent-py/src/louis_service.py` (3 methods)
- [ ] Response templates in `agent-py/src/response_templates.py` (4 templates)
- [ ] Red-flag detector in `agent-py/src/louis/red_flag_detector.py`
- [ ] ElevenLabs wrapper in `agent-py/src/louis/elevenlabs_wrapper.py`
- [ ] Agent entry point wired in `agent-py/src/agent.py`
- [ ] Unit tests: `tests/test_red_flag_detector.py`, `tests/test_mongo_logger.py`
- [ ] Demo fallback in `hackathon_mvp/hard_coded_scenarios.py`
- [ ] Demo script in `hackathon_mvp/demo_script.py`

---

**Before generating code:** Read this file + check `.claude/CLAUDE.md` for routing.
