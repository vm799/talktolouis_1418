"""Talk to Louis — LiveKit voice agent entrypoint.

Wires LouisAgent (safety-first voice assistant) into the LiveKit session pipeline.
Uses Deepgram STT, Cartesia TTS, Silero VAD, ai-coustics noise cancellation.
All spoken responses are pre-approved NHS-cited templates via LouisService.
"""

import json
import logging

from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    TurnHandlingOptions,
    cli,
    inference,
    room_io,
)
from livekit.plugins import ai_coustics, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from db.client import aclose, get_db
from agents.louis_agent import LouisAgent
from louis_service import LouisService
from data_domain.mongo_event_repo import MongoEventRepository

load_dotenv(".env.local")

logger = logging.getLogger("agent")

DEFAULT_USER_ID = "user_1"
DEFAULT_TENANT_ID = "default"


async def on_session_end(ctx: JobContext) -> None:
    """Persist session report to MongoDB on hangup."""
    try:
        report = ctx.make_session_report()
        db = await get_db()
        user_id = ctx.proc.userdata.get("user_id", DEFAULT_USER_ID)
        tenant_id = ctx.proc.userdata.get("tenant_id", DEFAULT_TENANT_ID)
        await db.sessions.insert_one(
            {
                "session_id": ctx.room.name,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "room_name": ctx.room.name,
                "report": report.to_dict(),
            }
        )
        logger.info("Persisted session report for %s", ctx.room.name)
    except Exception:
        logger.exception("Failed to persist session report")
    finally:
        await aclose()


server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="louis", on_session_end=on_session_end)
async def louis_session(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name}

    meta: dict[str, str] = {}
    if ctx.job.metadata:
        try:
            meta = json.loads(ctx.job.metadata)
        except json.JSONDecodeError:
            logger.warning("ctx.job.metadata was not valid JSON; using defaults")

    user_id = meta.get("user_id", DEFAULT_USER_ID)
    tenant_id = meta.get("tenant_id", DEFAULT_TENANT_ID)
    ctx.proc.userdata["user_id"] = user_id
    ctx.proc.userdata["tenant_id"] = tenant_id

    db = await get_db()
    mongo_repo = MongoEventRepository(db)
    louis_service = LouisService(mongo_repo=mongo_repo)
    agent = LouisAgent(
        session_id=ctx.room.name,
        user_id=user_id,
        tenant_id=tenant_id,
        louis_service=louis_service,
    )

    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="multi"),
        llm=inference.LLM(model="openai/gpt-4o-mini"),
        tts=inference.TTS(
            model="cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
        ),
        vad=ctx.proc.userdata["vad"],
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
            preemptive_generation={"enabled": True},
        ),
    )

    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_L
                ),
            ),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
