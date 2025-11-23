# FILE_PATH: C:\Users\amank\Desktop\agents\ten-days-of-voice-agents-2025\backend\src\agent.py
"""
Minimal LiveKit Agents `agent.py` that creates a talking AI agent.
- Uses Deepgram for STT (needs DEEPGRAM_API_KEY in .env.local)
- Uses Gemini LLM via livekit.plugins.google (needs GOOGLE_API_KEY)
- Uses Murf Falcon TTS when MURF_API_KEY is set; otherwise falls back to Google TTS

Drop this file in backend/src/agent.py and run:
    uv run python src/agent.py dev

Make sure your .env.local (in backend/) contains at least:
LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, DEEPGRAM_API_KEY, GOOGLE_API_KEY
For Murf Falcon: MURF_API_KEY (optional, used if present)

Notes:
- Google TTS streaming requires Application Default Credentials; Murf Falcon is preferred for simple API-key usage.
- If you experience connection errors with Murf, verify the MURF_API_KEY and network access.
"""

import logging
from dotenv import load_dotenv
import os

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
    MetricsCollectedEvent,
)

# Plugins
from livekit.plugins import deepgram, google, silero, noise_cancellation
# murf plugin in this repo may be local; import if available
try:
    from livekit.plugins import murf
except Exception:
    murf = None

from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

# Load env from backend/.env.local
load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful voice AI assistant."
                " Answer the user's questions concisely and speak via TTS."
            ),
        )


def prewarm(proc: JobProcess):
    # load silero VAD model into process userdata for faster startup
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # add room to logs
    ctx.log_context_fields = {"room": ctx.room.name}

    # select TTS provider: prefer Murf if API key present and plugin is available
    murf_key = os.getenv("MURF_API_KEY")
    if murf and murf_key:
        tts_provider = murf.TTS(model="falcon")
        logger.info("Using Murf Falcon TTS")
    else:
        # fallback to Google TTS (may require ADC setup)
        tts_provider = google.TTS()
        logger.info("Using Google TTS fallback")

    # Create the agent session
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=tts_provider,
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    # metrics
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        logger.info(f"Usage: {usage_collector.get_summary()}")

    ctx.add_shutdown_callback(log_usage)

    # Start session and connect
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
