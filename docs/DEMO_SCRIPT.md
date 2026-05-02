# DEMO_SCRIPT.md — 3-Minute Pitch Runbook

**Audience:** Hackathon judges  
**Duration:** 3 minutes (hard cap)  
**One-line framing:** *"AI interprets intent. The system executes deterministic coordination logic using event history."*

**What we are demoing:** A **coordination engine** that manages post-screening patient journeys over time. Most systems respond to inputs. Ours maintains state, manages tasks, and coordinates decisions over time.

**Pre-demo setup (do before walking in):**
- MongoDB Atlas tab open on `louis_audit_log` collection
- Frontend tab open on the session view
- Terminal visible (for the kill-session moment)
- `.env.local` loaded; ping MongoDB on startup; confirm green
- Demo fallback (`hackathon_mvp/demo_script.py`) available if voice path fails

---

## [0:00 – 0:20] Opening — Frame the system

**Presenter says (verbatim):**
> "This is a coordination engine that manages patient journeys after diabetic eye screening. It is not a chatbot. AI interprets intent. The system executes deterministic coordination logic using event history. Every turn is logged to MongoDB before any output is emitted, and state is reconstructed from that log on every interaction."

**What judge sees:**
- Slide / frontend home with patient session ready to start
- MongoDB Atlas tab visible in the corner: `louis_audit_log` collection (currently empty or filtered to demo session)

**Key talking points:**
- Coordination engine, not a chatbot
- Event-logged memory in MongoDB
- AI scoped to intent interpretation only
- Voice access is a clinical accessibility necessity (not a UX choice)

---

## [0:20 – 0:50] Greeting moment — Patient completes screening, system coordinates

**Presenter says (verbatim):**
> "The patient has just finished screening. Their pupils are dilated — they cannot safely read a screen. Voice is the only viable interface. The session coordinator logs a `screening_completed` event, derives state from the event history, and selects the post-screening greeting template. Every clinical phrase is hard-coded and cited to NICE or NHS — no LLM is generating patient-facing text."

**What judge sees:**
- Frontend triggers session start
- Voice (ElevenLabs) speaks the greeting template
- MongoDB tab refreshes — new document appears: `event_type: "screening_completed"`, `response_type: "greeting"`, `red_flag_status: false`
- Session state visibly transitions: `waiting_post_screening` → `post_screening`

**Key talking points:**
- Event logged *before* response is emitted (audit fence)
- State is derived from events, not held in memory
- Template is cited (NICE NG242)

**Likely judge questions + scripted answers:**
- *"Why not let the LLM speak directly?"* — "Safety. Patient-facing clinical text must be deterministic, cited, and testable. LLM synthesis on the patient path is an ADR-001 violation."
- *"Why voice?"* — "After pharmacological dilation, patients cannot safely read screens. Voice is the only viable interface for post-screening coordination."

---

## [0:50 – 1:30] Question moment — Intent interpretation drives template selection

**Presenter says (verbatim):**
> "The patient asks a question. The intent interpreter — that is the only place AI runs — classifies the intent. The coordination engine takes that intent, looks at the derived state from event history, and selects the right deterministic template. Same input, same state — same response. Every time. That is how we make a clinical workflow auditable."

**Demo input:** *"What happens next?"*

**What judge sees:**
- Voice input captured
- Frontend shows intent classification result (e.g. `intent: explanation, confidence: 0.92`)
- Voice plays the `explanation` template
- MongoDB tab updates: new event `event_type: "question"`, `response_type: "explanation"`, `red_flag_status: false`
- Event log now shows two documents in chronological order

**Key talking points:**
- AI is a classifier, not a generator
- Template is selected based on intent **plus** state derived from event history
- Determinism = compliance + reliability
- Citations preserved (NHS)

**Likely judge questions + scripted answers:**
- *"What if the classifier is wrong?"* — "Keyword fallback. If AI is uncertain, times out, or fails, the system falls back to a deterministic keyword classifier. The coordination engine never hangs on AI."
- *"How is this different from a chatbot?"* — "A chatbot generates responses. We coordinate decisions based on event history. The output is always a hard-coded template; the only variable is which template the engine selects."

---

## [1:30 – 2:00] Red flag moment — Safety fence, no negotiation

**Presenter says (verbatim):**
> "Now watch what happens when the patient says something that suggests an emergency. The safety fence runs first, on every turn, before anything else. No negotiation, no AI in the loop. Keyword match → escalation template → log → done."

**Demo input:** *"I'm seeing flashing lights"*

**What judge sees:**
- Voice input captured
- Frontend visibly flags red flag status (banner, colour change)
- Voice plays the `escalation` template ("Please call NHS 111 or 999...")
- MongoDB tab updates: event with `event_type: "red_flag"`, `red_flag_status: true`, `escalation_status: true`
- Session state transitions to `escalated`

**Key talking points:**
- Red-flag detection runs on every turn — silence is a failure mode
- Keyword-based, not ML — fast, testable, auditable
- Once escalated, the engine stays escalated (state is sticky via event replay)
- Escalation template cites NHS Emergency

**Likely judge questions + scripted answers:**
- *"Why not use an ML safety classifier?"* — "Latency, opacity, and edge cases. Keyword detection is bounded, testable, and instantly explainable to a clinical reviewer. We will not gamble patient safety on probabilistic models."
- *"What if the patient mistypes or speaks ambiguously?"* — "The fence is intentionally over-sensitive. Better to escalate a borderline case than miss a real one. Cost of false positive: a phone call. Cost of false negative: harm."

---

## [2:00 – 2:40] Kill-session moment — State reconstructed from event log (THE JUDGE MOMENT)

**Presenter says (verbatim):**
> "Here is the part most chat systems cannot do. I'm going to kill the session right now."

*[Presenter visibly closes the browser tab / kills the terminal process / refreshes the page.]*

> "Session is gone. Process is dead. Now I reload."

*[Presenter reloads the frontend or restarts the agent.]*

> "The session has been fully reconstructed from MongoDB. The escalated state is preserved. The audit trail is intact. No context is lost. This is what we mean by 'coordination over time' — the system maintains state across interruptions because state lives in the event log, not in memory."

**What judge sees:**
- Browser tab closed / terminal process killed (visibly)
- Reload / restart
- Frontend immediately reflects `escalated` state — escalation banner visible, escalation template available
- MongoDB tab: same documents still there, in order
- Terminal logs (if visible): `derive_state()` replays events → returns `"escalated"`

**Key talking points:**
- State is **derived**, not stored — `derive_state()` replays events at runtime
- This is event sourcing in miniature — MongoDB is the source of truth
- Session recovery is automatic; no special "resume" code path
- This is the difference between a chatbot and a coordination engine

**Likely judge questions + scripted answers:**
- *"Could you do this with Redis or in-memory state?"* — "You could, but you'd lose the audit trail. MongoDB gives us state recovery and a clinical-grade audit log in one component. One source of truth, two requirements satisfied."
- *"What about scale?"* — "Event log is append-only and indexed by `user_id` + timestamp. State derivation is bounded to a recent time window. Phase 2 adds TTL and event-stream sharding."
- *"What if MongoDB is down?"* — "Engine fails closed. No log = no response. We will not coordinate clinical decisions blind."

---

## [2:40 – 3:00] Close — The architectural thesis

**Presenter says (verbatim):**
> "We separate intelligence from execution to guarantee safety and reliability in clinical workflows. Most systems respond to inputs. Ours maintains state, manages tasks, and coordinates decisions over time. AI interprets intent. The system executes deterministic coordination logic using event history. That is how you build a clinical-grade voice access layer in four hours — and how it stays safe in production."

**What judge sees:**
- Final slide / frontend showing the full event log: greeting → question → red_flag → escalation
- MongoDB count: 4 events for one session, all immutable, all timestamped, all auditable

**Key talking points (closing reinforcement):**
- Coordination engine, not a chatbot
- Intelligence (AI) is separated from execution (templates + state machine)
- Voice is medical access, not a feature
- Safety and reliability are architectural, not bolted on

---

## Failure-mode quick reference (if something breaks mid-demo)

| Failure | Mitigation | Words to use |
|---|---|---|
| Voice does not play | Switch to `python hackathon_mvp/demo_script.py` text mode | "I'll show the same flow in the terminal — the engine logic is identical." |
| MongoDB connection drops | Show pre-recorded MongoDB screenshot | "Here is the event log from a clean run — the structure is the same." |
| Intent classifier times out | Show keyword fallback in action | "This is the keyword fallback. The engine never hangs on AI." |
| Red flag does not trigger | Run unit test live: `pytest tests/test_red_flag_detector.py` | "The detector is unit-tested. Here is the green run." |

---

## Post-demo — what to leave the judges with

One sentence, on the last slide:

> **"AI interprets intent. The system executes deterministic coordination logic using event history."**

That is the architecture. That is the safety thesis. That is why this is a coordination engine, not a chatbot.
