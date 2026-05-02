# BRD: Talk to Louis — One Page

**Status:** MVP (4-hour hackathon)  
**Product:** Voice-first diabetic eye screening companion  
**Target:** Hackathon demo (proof of concept)  

---

## PROBLEM

Patients with diabetes visit eye clinics for screenings but don't understand:
- What the results mean ("R2? Is that bad?")
- What happens next ("Why 6 months? When do I hear back?")
- When to worry ("Is my floater normal?")

**Frustration point:** No post-screening guidance. Patients leave confused, anxious, or missing critical escalation info.

---

## SOLUTION

**Talk to Louis:** A 3-minute voice-based session coordination after screening. It is a coordination engine — not a chatbot. AI interprets intent. The system executes deterministic coordination logic using event history.

The engine:
1. Greets the patient + congratulates them on completing screening
2. Explains the grading system in plain English
3. Coordinates decisions based on event history (anxiety, timelines, next steps)
4. Detects red flags (sudden vision loss, pain) + escalates immediately to NHS 111
5. Logs every event to MongoDB so state can be reconstructed at any moment

**Uniqueness:**
- Voice access (clinical accessibility — after pharmacological dilation, patients cannot safely read screens)
- Constrained (4 safe phrases, no diagnosis, no LLM synthesis on the patient path)
- Safe by design (red-flag safety fence, hard-coded templates, MongoDB audit trail)
- Hackathon-proof (demo runs deterministically even if AI inference fails)

---

## SCOPE (MVP only)

### ✅ INCLUDED
- Voice greeting + post-screening reassurance
- 4 safe Q&A templates (hard-coded)
- Red-flag keyword detection
- Immediate escalation to NHS 111
- Full MongoDB audit trail (every event logged)
- Demo fallback (works without AI inference)
- ElevenLabs voice output
- 3-minute demo script

### ❌ NOT INCLUDED (Phase 2+)
- Retinal image analysis
- Full NHS pathway integration
- Multi-language support
- Video escalation
- FHIR/EHR integration
- Persistent login / authentication
- Production infrastructure (K8s, SRE, etc.)

---

## SUCCESS CRITERIA

| Criterion | How to Verify |
|---|---|
| Greets after screening | Demo Scenario 1 works |
| Explains plain English | Demo Scenario 2 works |
| Answers 4 safe questions | Demo Scenarios 2-3 work |
| Detects red flags | Demo Scenario 4 triggers escalation |
| Escalates safely | Demo Scenario 4: "Call NHS 111" output |
| Every event logged | Query MongoDB, find all 4 demo events |
| Demo runs 3 min (no AI inference) | Run hackathon_mvp/hard_coded_scenarios.py |
| Safe by design | Pass red-flag detector unit test |

---

## COMPETITORS / REFERENCE

- **RetinaRisk** (UK): Retinal image analysis + risk prediction (too complex)
- **myDiabetes** (NHS): Symptom tracker (too generic)
- **NHS Eye Screening Pathway** (gold standard): Post-screening guidance (manual, not automated)

**Our advantage:** Voice-first, zero diagnosis, 100% safe, auditable.

---

## PRODUCT NARRATIVE

> **Louis is the voice access layer that coordinates your post-screening journey in plain English.**
> 
> You finish screening. Your pupils are dilated; you cannot safely read a screen. Louis greets you, explains your grade, and coordinates decisions based on event history — all in your own time, in your own words.
> 
> If something sounds serious, the safety fence triggers and Louis routes you immediately to NHS 111. If not, Louis sends you on your way with confidence.
> 
> No algorithms generating clinical text. No predictions. No diagnosis. AI interprets intent; the system executes deterministic coordination logic using event history.

---

## BUSINESS MODEL (Phase 2)

- **SaaS for NHS Eye Clinics:** £500/month per clinic (unlimited patients)
- **Freemium:** Basic greeting (free) + escalation (paid)
- **Data insights:** Aggregate red-flag trends (anonymized, compliant)

---

## DEPENDENCIES (MVP)

- **LiveKit Cloud:** Voice transport (already have)
- **MongoDB Atlas:** Audit trail (already have)
- **ElevenLabs:** Voice output API (API key needed)
- **Fireworks AI:** Optional LLM inference (API key needed)
- **LangSmith:** Optional tracing (API key needed)

---

## RISKS & MITIGATION

| Risk | Impact | Mitigation |
|---|---|---|
| Fireworks API timeout | Demo fails | Hard-coded fallback scenarios |
| Red-flag not detected | Patient harm | Keyword-based detection (no ML) + manual testing |
| MongoDB audit missing | Compliance breach | Synchronous insert every event |
| ElevenLabs latency | Poor UX | Async TTS with 3-second timeout |
| Scope creep (add FHIR, etc.) | Miss deadline | Weekly CLAUDE.md review + ways-of-working.md enforcement |

---

## DEFINITION OF DONE (MVP)

- [ ] 4 demo scenarios work end-to-end
- [ ] Red-flag detector passes unit test (5 keywords)
- [ ] MongoDB audit trail: 4 events logged per demo run
- [ ] Demo runs 3 minutes without AI inference
- [ ] All code commented, no TODOs
- [ ] ways-of-working.md followed (no scope creep)
- [ ] 2 unit tests passing (red-flag, mongo-logger)
- [ ] Demo script + speaker notes written
- [ ] Git log shows micro-commits (one feature per commit)

---

## NEXT PHASE (Phase 2, Future)

After demo, add:
1. Full NHS pathway integration (R0-R4 grading explanations)
2. Multi-language support (10 languages)
3. Video escalation (for complex cases)
4. FHIR integration (EHR interop)
5. Production deployment (AWS, SRE, K8s)
6. Authentication (Clerk, NextAuth)
7. Multi-tenant support (multiple clinics)
8. Analytics dashboard (aggregate red-flag trends)

---

**Owner:** V (Process Pro AI)  
**Last updated:** 2026-05-02  
**Next review:** 2026-05-09 (post-demo retro)
