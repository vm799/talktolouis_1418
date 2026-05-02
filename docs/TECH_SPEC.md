# Tech Spec — Voice-First Event Coordination System

**See [ADR-001.md](./ADR-001.md) for architecture rationale.**

---

## 1. System Overview

A **coordination engine** for post-screening patient journeys. It is not a chatbot — it is an event-driven state machine with persistent memory that coordinates decisions over time.

AI interprets intent. The system executes deterministic coordination logic using event history.

Per turn, the engine:
1. Receives voice input from the patient
2. Interprets intent (AI classification only — no synthesis)
3. Derives current session state by replaying MongoDB event history
4. Selects a deterministic response template based on state + intent
5. Logs the event before any output is emitted

---

## 2. Architecture

| Layer | Component | Implementation |
|-------|-----------|-----------------|
| **Presentation** | Voice interface | LiveKit + TTS (ElevenLabs) |
| **Application** | Service orchestrator | `louis_service.py` (3 methods) |
| **Logic** | Intent + safety | Classification + red-flag detector |
| **State** | Event replay engine | `mongo_event_repo.derive_state()` |
| **Data** | Event store | MongoDB Atlas (`louis_audit_log`) |

---

## 3. Data Model

### Event Document (MongoDB)

```
{
  "_id": ObjectId,
  "session_id": "uuid",           # LiveKit room ID
  "user_id": "string",            # Patient alias
  "tenant_id": "string",          # Multi-tenant scoping
  "event_type": "string",         # Enum: see below
  "user_input": "string|null",    # What patient said (null for system events)
  "response_type": "string",      # Enum: see below
  "red_flag_status": boolean,     # True if red flag detected
  "escalation_status": boolean,   # True if escalated
  "timestamp": datetime           # UTC, ISO 8601
}
```

### Event Types

| Type | Trigger | Response | Escalates? |
|------|---------|----------|-----------|
| `screening_completed` | Session starts | Greeting template | No |
| `question` | User asks | Explanation or reassurance | Depends on content |
| `red_flag` | Keyword match | Escalation template | **Yes** |
| `escalation` | Red flag → NHS 111 | Escalation template | **Yes** |

### Response Types

| Type | Template | Citations | Safety Check |
|------|----------|-----------|--------------|
| `greeting` | Post-screening reassurance | NICE NG242 | No diagnosis |
| `explanation` | How eye screening works | NHS England | No diagnosis |
| `reassurance` | Normal feelings post-screening | NHS Diabetes | No diagnosis |
| `escalation` | NHS 111 + emergency pathway | NHS Emergency | Mandatory escalation |

---

## 4. Core Functions

### 4.1 Log Event (Mandatory Before Every Response)

```python
async def insert_event(entry: AuditLogEntry) -> str:
    """Insert event to MongoDB before any response sent.
    
    Violations: if event not logged, treat as system failure.
    """
    collection = db["louis_audit_log"]
    result = await collection.insert_one(entry.to_dict())
    return str(result.inserted_id)
```

---

### 4.2 Derive State (Event Replay)

```python
async def derive_state(user_id: str, hours: int = 4) -> str:
    """Reconstruct current state by replaying recent events.
    
    State machine:
    - waiting_post_screening: no screening event yet
    - post_screening: screening_completed event seen
    - escalated: red_flag or escalation event seen
    
    Returns deterministic state based on event history.
    """
    events = await get_events_by_user_recent(user_id, hours)
    state = "waiting_post_screening"
    
    for event in events:
        if event["event_type"] == "screening_completed":
            state = "post_screening"
        if event["event_type"] in ("red_flag", "escalation"):
            state = "escalated"
    
    return state
```

---

### 4.3 Red-Flag Detection (Non-Negotiable)

```python
def check(user_input: str) -> bool:
    """Keyword-based red flag detection.
    
    Returns True if any red flag keyword found.
    Policy: Must run on EVERY user input. Silence = failure.
    """
    red_flags = [
        "flashing", "curtain", "sudden vision loss",
        "pain", "emergency", "cant see", "blind"
    ]
    
    user_lower = user_input.lower()
    return any(flag in user_lower for flag in red_flags)
```

---

## 5. Intent Classification (AI Layer)

### Role
- Classify intent from user input
- Return structured output
- No response generation

### Example

**Input:** "What happens after the screening?"

**Output:**
```json
{
  "intent": "explanation",
  "confidence": 0.92
}
```

### Fallback (Keyword-Based)

```python
def keyword_fallback(text: str) -> str:
    """Fallback classifier (no AI).
    
    Used if:
    - AI service timeout
    - API error
    - Unclear classification
    """
    keywords = {
        "next": "explanation",
        "what": "explanation",
        "how": "explanation",
        "when": "explanation",
        "timeline": "explanation",
        "worried": "reassurance",
        "concerned": "reassurance",
        "scared": "reassurance",
    }
    
    text_lower = text.lower()
    for keyword, intent in keywords.items():
        if keyword in text_lower:
            return intent
    
    return "default"  # Fallback to generic reassurance
```

---

## 6. Routing Logic (CORE ORCHESTRATION)

```python
async def assess_question(
    session_id: str, user_id: str, user_input: str
) -> Tuple[str, bool]:
    """Main routing logic.
    
    1. Check state (derived from events)
    2. Log question
    3. Detect red flags (MANDATORY)
    4. Classify intent
    5. Select template
    6. Log response BEFORE returning
    7. Return template + escalation flag
    """
    
    # Step 1: Derive current state
    current_state = await mongo_repo.derive_state(user_id)
    
    # Step 2: If already escalated, stay escalated
    if current_state == "escalated":
        response = get_template("escalation")
        await mongo_repo.insert_event(...)  # Log escalation
        return response, True
    
    # Step 3: MANDATORY red-flag check
    is_red_flag = red_flag_detector.check(user_input)
    
    if is_red_flag:
        # Escalate immediately
        response = get_template("escalation")
        await mongo_repo.insert_event(...)  # Log red flag
        return response, True
    
    # Step 4: No red flag → classify intent
    intent = classify_intent(user_input)  # AI or fallback
    
    # Step 5: Select template based on intent
    if intent == "explanation":
        response = get_template("explanation")
    else:
        response = get_template("reassurance")
    
    # Step 6: Log BEFORE returning
    await mongo_repo.insert_event(...)
    
    # Step 7: Return
    return response, False
```

---

## 7. Voice Layer

**Voice access is a clinical accessibility necessity.** After pharmacological dilation, patients cannot safely read screens. Voice is the only viable interface for post-screening coordination.

### Input Pipeline
```
Speech → STT (LiveKit/Deepgram) → Text
Text → Intent Interpretation → Template Selection
```

### Output Pipeline
```
Template → Safety Check → TTS (ElevenLabs) → Speech
Speech → VoIP (LiveKit) → Patient
```

---

## 8. Failure Handling

| Failure | Behavior | Logging |
|---------|----------|---------|
| AI classification timeout | Fallback to keyword classifier | Logged as fallback |
| MongoDB insert fails | Retry 3x, then log error | Error event logged |
| Voice output fails | Return text template | Logged as TTS failure |
| Red-flag detector missing | **TREAT AS CRITICAL** | Escalate, log error |
| Event not logged | **TREAT AS CRITICAL** | System failure, escalate |

---

## 9. Demo Requirements

**Must visibly demonstrate:**

1. ✅ MongoDB event log populated
2. ✅ State changing based on events
3. ✅ Red-flag detection → escalation
4. ✅ Session recovery after refresh
5. ✅ Deterministic outputs (same input = same response)

---

## 10. Performance Targets

- Response time: < 2 seconds (including TTS)
- Event logging: < 100ms (async)
- State derivation: < 50ms (MongoDB query)
- Zero crashes during demo

---

## 11. Demo Flow (3 minutes)

```
1. Start session
   → Log screening_completed event
   → Show greeting

2. Ask normal question ("What happens next?")
   → Log question event
   → Show explanation template

3. Ask red-flag question ("I see flashing lights")
   → Log red_flag event
   → Log escalation_triggered event
   → Show escalation template

4. Refresh page
   → State persists (escalated)
   → Show escalation template again
   → Demonstrate event-based recovery
```

---

## 12. Summary

A coordination engine that manages patient journeys over time, not a system that responds to inputs.

- **Coordination over time** — State is reconstructed from event history on every turn; behaviour persists across interruptions via event replay
- **AI interprets, system decides** — AI classifies intent only; the system executes deterministic coordination logic using event history
- **Event-based memory** — MongoDB is the persistent context engine; every turn is logged before any output is emitted
- **Safe routing** — Deterministic templates + red-flag safety fence; no LLM synthesis on the patient-facing path
- **Session recovery** — A killed session reconstructs full state from MongoDB on resume; no context is lost
