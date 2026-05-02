# GOTCHAS.md — Known Issues (Save 30 minutes per mistake)

**Updated:** 2026-05-02  
**Use:** Before debugging, check here first  
**Reminder:** This is a coordination engine. AI interprets intent; the system executes deterministic coordination logic using event history. Most gotchas below protect that contract.  

---

## Gotcha 1: Voyage Embeddings API Rate Limit

**Problem:** Free tier Voyage API rate-limited to 5 req/sec. If you call embed_text() more than 5 times per second, you get 429 errors.

**Where it hurts:** If red-flag detector uses vector search (it shouldn't), it will fail on high volume.

**Solution:** Use keyword matching only (no embeddings). Red flags are simple string matches.

**Prevention:** Always use `RedFlagDetector.check()` (keyword-based), never use `embed_text()` in red-flag path.

---

## Gotcha 2: LangGraph State Persists in Memory (Loses on Restart)

**Problem:** If you add a LangGraph state machine for orchestration, it lives in memory. When agent restarts (deploy, crash, etc.), all state is lost.

**Where it hurts:** Session context lost, user has to start over, audit trail incomplete. State must be reconstructable from the event log; if it lives in memory, it is gone on restart.

**Solution:** Don't use LangGraph state for MVP. Use MongoDB as single source of truth — state is derived from event history, not held in memory.

**Prevention:** Treat MongoDB as the state store. Every coordination decision logged immediately. LiveKit turn-handling is enough orchestration.

---

## Gotcha 3: Fireworks Inference Takes 2-5 Seconds per Turn

**Problem:** Remote LLM inference (Fireworks AI) has latency. If you try to synthesise a response on every turn, users experience long pauses — and you have broken the architectural contract (AI interprets intent only, never generates patient-facing output).

**Where it hurts:** 3-minute demo becomes 10 minutes (4 turns × 3-5 sec = 12-20 sec minimum).

**Solution:** Hard-code 4 response templates. Use Fireworks only for intent classification, never for response synthesis.

**Prevention:** Build demo with hard-coded templates. The coordination engine selects from templates; AI only interprets intent.

---

## Gotcha 4: ElevenLabs Voice Latency ~1 Second

**Problem:** TTS (text-to-speech) API call takes ~1 second to get audio bytes. If you do this synchronously in the turn handler, it blocks the entire interaction.

**Where it hurts:** User hears long delay before Louis speaks.

**Solution:** TTS happens async in background. Don't wait for it to complete before returning response text.

**Prevention:** Wrap TTS in `asyncio.wait_for(..., timeout=3.0)`. If timeout, play fallback audio or text-only.

---

## Gotcha 5: MongoDB Atlas Vector Indexes Take 1-2 Minutes to Be Queryable

**Problem:** When you create a vector index in MongoDB Atlas, it doesn't immediately become queryable. You have to wait 1-2 minutes.

**Where it hurts:** If you run `db:init` (create indexes), then immediately `db:seed` (populate data), then query — the vector search returns nothing.

**Solution:** Run `db:init`, wait 2 minutes, then proceed.

**Prevention:** In CI/CD, add explicit wait after index creation. For hackathon, do this step early, then go do something else for 2 min.

---

## Gotcha 6: Red-Flag Detection Must Fire Before Any Other Logic

**Problem:** If you don't check red flags first, you might return a reassurance response when the user said "I'm having a stroke." Critical safety issue.

**Where it hurts:** Patient harm, regulatory violation, demo failure.

**Solution:** Check red flags on EVERY turn, before any other logic. Hard rule.

```python
# DO THIS FIRST
if red_flag_detector.check(user_input):
    return escalate()

# Then do everything else
```

**Prevention:** Put red-flag check at the top of `assess_question()`. Comment it as "NON-NEGOTIABLE".

---

## Gotcha 7: async/await Syntax Errors (Common in Python)

**Problem:** If you mix async and sync code, you get cryptic errors:
```
RuntimeError: no running event loop
AttributeError: coroutine object has no attribute 'result'
TypeError: object is not iterable
```

**Where it hurts:** Agent crashes on first red-flag query (which is async).

**Solution:** Always use `await` when calling async functions. Always make methods `async def`.

```python
# ❌ WRONG
response = self.mongo_repo.insert_event(entry)

# ✅ RIGHT
response = await self.mongo_repo.insert_event(entry)
```

**Prevention:** Use `async def` consistently. Search codebase for `.insert_event(` (should be `await` before it).

---

## Gotcha 8: MongoDB Connection String Format

**Problem:** If MONGODB_URI is missing or malformed, `pymongo` hangs for 30 seconds before failing.

**Where it hurts:** First query hangs, demo looks broken, judge thinks it crashed.

**Solution:** Test MongoDB connection early. Fail fast if connection fails.

```python
@app.on_startup
async def startup():
    try:
        await get_db().admin.command('ping')
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"❌ MongoDB failed: {e}")
        raise
```

**Prevention:** In agent startup, ping MongoDB immediately. If it fails, print error and exit (don't hang).

---

## Gotcha 9: .env Variables Not Loaded (Missing `dotenv.load_dotenv()`)

**Problem:** You set ELEVENLABS_API_KEY in `.env`, but the code doesn't see it. `os.getenv("ELEVENLABS_API_KEY")` returns None.

**Where it hurts:** TTS wrapper silently falls back, voice output disappears.

**Solution:** Call `dotenv.load_dotenv(".env.local")` at the very top of your entry point.

```python
# agent-py/src/agent.py - TOP OF FILE
from dotenv import load_dotenv
load_dotenv(".env.local")
```

**Prevention:** Check that `.env.local` exists and has values. Print them on startup: `print(f"ELEVENLABS_API_KEY={os.getenv('ELEVENLABS_API_KEY')}")`.

---

## Gotcha 10: Forgetting to Import New Modules

**Problem:** You create `agent-py/src/louis_service.py` but forget to import it in `agent.py`. Python silently ignores the file.

**Where it hurts:** Demo runs but does nothing (no output, no error).

**Solution:** Explicitly import in `agent.py`:
```python
from agent_py.src.louis_service import LouisService
```

**Prevention:** After creating a new module, grep for it in main entry point: `grep -r "LouisService" agent-py/src/`.

---

## Gotcha 11: User Input Empty or None

**Problem:** If user doesn't say anything, LiveKit returns empty string `""`. If you try to check red flags on empty string, it might match.

**Where it hurts:** Empty utterance triggers false red flag.

**Solution:** Filter empty input before processing.

```python
def handle_turn(user_input: str):
    if not user_input or not user_input.strip():
        return get_template("fallback")
    # Then proceed
```

**Prevention:** Always call `.strip()` and check length.

---

## Gotcha 12: MongoDB Audit Log Grows Unbounded

**Problem:** After running demo 10 times, you have 40 audit log entries. No TTL, so they persist forever.

**Where it hurts:** Not immediately, but analytics queries slow down.

**Solution:** For MVP, don't worry. For Phase 2, add TTL index.

**Prevention:** Document for Phase 2: "Add TTL index to louis_audit_log (30 days retention)".

---

## Gotcha 13: TypeError on async context (asyncio.run vs await)

**Problem:** You try to call an async function from synchronous code, or vice versa.

```python
# ❌ WRONG - async function not awaited
result = mongo_repo.insert_event(entry)  # This is a coroutine, not the result

# ✅ RIGHT - async function in async context
result = await mongo_repo.insert_event(entry)

# ✅ RIGHT - async function from sync code
asyncio.run(mongo_repo.insert_event(entry))
```

**Where it hurts:** Random TypeError crashes.

**Solution:** Be consistent about async/sync boundaries.

**Prevention:** Add type hints: `async def insert_event(...) -> str:`. Linter will catch mismatches.

---

## Gotcha 14: LiveKit Turn Detection Breaks on Very Short Utterances

**Problem:** If user says one word ("Yes"), LiveKit might not detect end-of-turn properly. Agent waits for more input, demo hangs.

**Where it hurts:** If demo participant speaks quietly, turn detection fails.

**Solution:** Set turn detection sensitivity. For MVP, use demo script (predefined inputs).

**Prevention:** In demo script, paste full utterances (not single words). Test with live speech before demo.

---

## Gotcha 15: Escalation Doesn't Stop the Turn Handler

**Problem:** You detect a red flag and return escalation response, but the turn handler keeps running. Maybe it tries to log again, or call TTS twice.

**Where it hurts:** Duplicate events, double TTS, slow response.

**Solution:** When escalating, return immediately. Don't fall through to other logic.

```python
async def assess_question(...):
    if red_flag_detector.check(user_input):
        response = get_template("escalation")
        entry = AuditLogEntry(...)
        await self.mongo_repo.insert_event(entry)
        return response  # ← RETURN HERE, don't continue
    
    # Other logic only if no red flag
    ...
```

**Prevention:** Use `if/else`, not `if` + more code after.

---

## Quick Debugging Checklist

If demo breaks:

1. **Agent doesn't start?**
   - Check `.env.local` exists
   - Run `dotenv.load_dotenv(".env.local")`
   - Print all env vars on startup

2. **Red-flag detector doesn't trigger?**
   - Test red-flag locally: `python -c "from louis.red_flag_detector import *; print(RedFlagDetector.check('flashing lights'))"`
   - Should print `True`

3. **MongoDB events not logging?**
   - Check MONGODB_URI in `.env`
   - Ping MongoDB: `python -c "from pymongo import AsyncClient; ..."`
   - Query collection: `db.louis_audit_log.find()` in MongoDB Atlas

4. **TTS latency too high?**
   - Test TTS: `curl -X POST https://api.elevenlabs.io/v1/text-to-speech/... -H "xi-api-key: $ELEVENLABS_API_KEY"`
   - Should respond <2 sec

5. **Fireworks API timeout?**
   - Check FIREWORKS_API_KEY
   - Test fallback: hard-coded scenarios working?

6. **Demo script runs but no output?**
   - Check imports: `grep -r "from agent_py" agent-py/src/`
   - Check function calls: `grep -r "LouisService" agent-py/`

---

**When stuck:** Read `.claude/ways-of-working.md` + this file before asking for help.

**When debugging:** Commit before you break it. `git diff` shows what changed.

---

**Owner:** V (Process Pro AI)  
**Last updated:** 2026-05-02  
**Next review:** After first demo run
