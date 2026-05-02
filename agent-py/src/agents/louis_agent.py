"""LouisAgent — safety-first voice agent for Talk to Louis.

Wraps LouisService with LiveKit Agent lifecycle.
All spoken responses are pre-approved NHS-cited templates — no LLM freeform text.

Flow:
    on_enter       → greeting() → session.say(template)
    user speaks    → assess_question() → session.say(template)
    red flag       → escalate()  → session.say(template) → log → session end
"""

import logging

from livekit.agents import Agent, RunContext, function_tool

from louis_service import LouisService

logger = logging.getLogger("louis_agent")

LOUIS_INSTRUCTIONS = (
    "You are Louis, a post-screening voice assistant for NHS diabetic eye screening. "
    "SAFETY RULE: You must NEVER generate medical advice, diagnoses, or opinions. "
    "When the patient speaks, ALWAYS call handle_patient_input with their exact words. "
    "Say ONLY what the tool returns — do not add, remove, or rephrase anything. "
    "If the tool is unavailable, say: 'I'm having trouble right now. "
    "For urgent advice please call NHS 111.'"
)


class LouisAgent(Agent):
    """Voice agent that routes all patient speech through LouisService templates."""

    def __init__(
        self,
        *,
        session_id: str,
        user_id: str,
        tenant_id: str,
        louis_service: LouisService,
    ) -> None:
        super().__init__(instructions=LOUIS_INSTRUCTIONS)
        self._session_id = session_id
        self._user_id = user_id
        self._tenant_id = tenant_id
        self._louis_service = louis_service

    async def on_enter(self) -> None:
        """Speak greeting on session start — bypasses LLM for safety."""
        try:
            response_text, _ = await self._louis_service.greeting(
                session_id=self._session_id,
                user_id=self._user_id,
                tenant_id=self._tenant_id,
            )
            await self.session.say(response_text)
        except Exception:
            logger.exception("Greeting failed")
            await self.session.say(
                "Hello, I'm Louis. I'm here to support you after your eye screening. "
                "For urgent advice please call NHS 111."
            )

    @function_tool()
    async def handle_patient_input(
        self, context: RunContext, patient_speech: str
    ) -> str:
        """Route patient speech through safety checks and return pre-approved response.

        Always call this tool when the patient speaks.
        Returns the exact text Louis should say — do not modify the returned string.
        """
        try:
            response_text, should_escalate = await self._louis_service.assess_question(
                session_id=self._session_id,
                user_id=self._user_id,
                user_input=patient_speech,
                tenant_id=self._tenant_id,
            )

            if should_escalate:
                logger.warning(
                    "ESCALATION: session=%s user=%s input=%r",
                    self._session_id,
                    self._user_id,
                    patient_speech,
                )

            return response_text

        except Exception:
            logger.exception("assess_question failed")
            return (
                "I'm having trouble right now. "
                "For urgent medical advice please call NHS 111."
            )
