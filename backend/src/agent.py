import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Annotated, Literal
from dataclasses import dataclass, field

from dotenv import load_dotenv
from pydantic import Field
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    tokenize,
    metrics,
    MetricsCollectedEvent,
    RunContext,
    function_tool,
)

from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")
load_dotenv(".env.local")

# ------------------------------------------------------------------
# Cafeteria AI Barista (Jarvis-style)
# - Shop name: Cafeteria
# - Personality: Polished, efficient, slightly witty (in the spirit of Jarvis)
# - All credits and tutorial references removed
# - No emojis
# - Extra: recommendations/upsells, small-talk handler, order persistence
# ------------------------------------------------------------------

@dataclass
class OrderState:
    """Coffee shop order state with validation"""
    drinkType: str | None = None
    size: str | None = None
    milk: str | None = None
    extras: list[str] = field(default_factory=list)
    name: str | None = None

    def is_complete(self) -> bool:
        return all([
            self.drinkType is not None,
            self.size is not None,
            self.milk is not None,
            self.extras is not None,
            self.name is not None
        ])

    def to_dict(self) -> dict:
        return {
            "drinkType": self.drinkType,
            "size": self.size,
            "milk": self.milk,
            "extras": self.extras,
            "name": self.name
        }

    def get_summary(self) -> str:
        if not self.is_complete():
            return "Order in progress"

        extras_text = f" with {', '.join(self.extras)}" if self.extras else ""
        return f"{self.size.title()} {self.drinkType.title()} with {self.milk.title()} milk{extras_text} for {self.name}"

@dataclass
class Userdata:
    order: OrderState
    session_start: datetime = field(default_factory=datetime.now)

# -----------------------
# Function tools
# -----------------------

@function_tool
async def set_drink_type(
    ctx: RunContext[Userdata],
    drink: Annotated[
        Literal["latte", "cappuccino", "americano", "espresso", "mocha", "coffee", "cold brew", "matcha"],
        Field(description="The type of coffee drink the customer wants"),
    ],
) -> str:
    ctx.userdata.order.drinkType = drink
    logger.info(f"DRINK SET: {drink}")
    return f"Understood. One {drink}, noted. What size would you prefer?"

@function_tool
async def set_size(
    ctx: RunContext[Userdata],
    size: Annotated[
        Literal["small", "medium", "large", "extra large"],
        Field(description="The size of the drink"),
    ],
) -> str:
    ctx.userdata.order.size = size
    logger.info(f"SIZE SET: {size}")
    return f"{size.title()} size set. Any milk preference?"

@function_tool
async def set_milk(
    ctx: RunContext[Userdata],
    milk: Annotated[
        Literal["whole", "skim", "almond", "oat", "soy", "coconut", "none"],
        Field(description="The type of milk for the drink"),
    ],
) -> str:
    ctx.userdata.order.milk = milk
    logger.info(f"MILK SET: {milk}")
    if milk == "none":
        return "Black coffee, excellent. Any extras or add-ons?"
    return f"{milk.title()} milk selected. Any extras?"

@function_tool
async def set_extras(
    ctx: RunContext[Userdata],
    extras: Annotated[
        list[Literal["sugar", "whipped cream", "caramel", "extra shot", "vanilla", "cinnamon", "honey"]] | None,
        Field(description="List of extras, or empty/None for no extras"),
    ] = None,
) -> str:
    ctx.userdata.order.extras = extras if extras else []
    logger.info(f"EXTRAS SET: {ctx.userdata.order.extras}")
    if ctx.userdata.order.extras:
        return f"Added {', '.join(ctx.userdata.order.extras)}. May I have the name for the order?"
    return "No extras. May I have the name for the order?"

@function_tool
async def set_name(
    ctx: RunContext[Userdata],
    name: Annotated[str, Field(description="Customer's name for the order")],
) -> str:
    ctx.userdata.order.name = name.strip().title()
    logger.info(f"NAME SET: {ctx.userdata.order.name}")
    return f"Thank you, {ctx.userdata.order.name}. Would you like me to complete the order now?"

@function_tool
async def complete_order(ctx: RunContext[Userdata]) -> str:
    order = ctx.userdata.order
    if not order.is_complete():
        missing = []
        if not order.drinkType: missing.append("drink type")
        if not order.size: missing.append("size")
        if not order.milk: missing.append("milk")
        if order.extras is None: missing.append("extras")
        if not order.name: missing.append("name")
        return f"Almost there. I still need: {', '.join(missing)}"

    try:
        path = save_order_to_json(order)
        logger.info(f"Order saved to {path}")
        extras_text = f" with {', '.join(order.extras)}" if order.extras else ""
        return (
            f"Order confirmed: {order.get_summary()}. It will be ready in about 3-5 minutes. "
            "Thank you for choosing Cafeteria."
        )
    except Exception as e:
        logger.exception("Failed to save order")
        return "There was an error saving your order. I have noted it internally and will prepare it regardless."

@function_tool
async def get_order_status(ctx: RunContext[Userdata]) -> str:
    order = ctx.userdata.order
    if order.is_complete():
        return f"Your order is complete: {order.get_summary()}"
    return f"Order in progress: {order.get_summary()}"

@function_tool
async def recommend_addon(ctx: RunContext[Userdata]) -> str:
    # Simple recommendation logic: upsell a pastry or extra shot
    order = ctx.userdata.order
    suggestions = []
    if order.size in ("large", "extra large"):
        suggestions.append("Would you like an extra shot to boost that?")
    suggestions.append("We have a fresh croissant if you want a snack with that.")
    return " ".join(suggestions)

# -----------------------
# Agent definition
# -----------------------
class CafeteriaAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "You are an intelligent, efficient assistant named Cafeteria AI. "
                "Speak in a calm, polished, slightly witty manner similar to a personal assistant. "
                "Keep answers concise and helpful. Ask one question at a time. Use the provided function tools to collect order details. "
                "If the user asks a non-order question, respond helpfully (small talk allowed)."
            ),
            tools=[
                set_drink_type,
                set_size,
                set_milk,
                set_extras,
                set_name,
                complete_order,
                get_order_status,
                recommend_addon,
            ],
        )

# -----------------------
# Persistence helpers
# -----------------------

def get_orders_folder():
    base_dir = os.path.dirname(__file__)
    backend_dir = os.path.abspath(os.path.join(base_dir, ".."))
    folder = os.path.join(backend_dir, "orders")
    os.makedirs(folder, exist_ok=True)
    return folder


def save_order_to_json(order: OrderState) -> str:
    folder = get_orders_folder()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"order_{timestamp}.json"
    path = os.path.join(folder, filename)
    order_data = order.to_dict()
    order_data["timestamp"] = datetime.now().isoformat()
    order_data["session_id"] = f"session_{timestamp}"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(order_data, f, indent=4, ensure_ascii=False)
    return path

# -----------------------
# Prewarm
# -----------------------

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("VAD model prewarmed")

# -----------------------
# Entrypoint
# -----------------------
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    logger.info("Starting Cafeteria AI session")

    userdata = Userdata(order=OrderState())

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(voice="en-US-matthew"),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        userdata=userdata,
        preemptive_generation=True,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        logger.info(f"Usage summary: {usage_collector.get_summary()}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=CafeteriaAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

# -----------------------
# CLI
# -----------------------
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
