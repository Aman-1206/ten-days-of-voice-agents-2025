import json
import logging
import os
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Annotated

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
    function_tool,
    RunContext,
)

from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# -------------------------
# Logging
# -------------------------
logger = logging.getLogger("voice_louis_vuitton")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

load_dotenv(".env.local")

# -------------------------
# Louis Vuitton Style Catalog
# -------------------------
# Sizes converted: small, medium, large, extra-large
CATALOG = [
    {
        "id": "lv-bag-001",
        "name": "Louis Vuitton Monogram Tote",
        "description": "Classic LV monogram tote, premium leather.",
        "price": 95000,
        "currency": "INR",
        "category": "bag",
        "color": "brown",
        "sizes": [],
    },
    {
        "id": "lv-shirt-001",
        "name": "LV Signature T-Shirt",
        "description": "Premium cotton LV T-shirt with logo emboss.",
        "price": 25000,
        "currency": "INR",
        "category": "tshirt",
        "color": "white",
        "sizes": ["small", "medium", "large", "extra-large"],
    },
    {
        "id": "lv-hoodie-001",
        "name": "LV Black Luxury Hoodie",
        "description": "Soft-touch luxury hoodie with LV chest logo.",
        "price": 45000,
        "currency": "INR",
        "category": "hoodie",
        "color": "black",
        "sizes": ["medium", "large", "extra-large"],
    },
    {
        "id": "lv-shoes-001",
        "name": "LV Leather Sneakers",
        "description": "Premium leather sneakers with embossed LV pattern.",
        "price": 60000,
        "currency": "INR",
        "category": "shoes",
        "color": "white",
        "sizes": ["small", "medium", "large"],
    },
    {
        "id": "lv-wallet-001",
        "name": "LV Compact Wallet",
        "description": "Compact men's wallet with iconic monogram.",
        "price": 32000,
        "currency": "INR",
        "category": "wallet",
        "color": "brown",
        "sizes": [],
    }
]

ORDERS_FILE = "orders.json"

# ensure orders file exists
if not os.path.exists(ORDERS_FILE):
    with open(ORDERS_FILE, "w") as f:
        json.dump([], f)

# -------------------------
# Per-session Userdata
# -------------------------
@dataclass
class Userdata:
    customer_name: Optional[str] = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    cart: List[Dict] = field(default_factory=list)
    orders: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)

# -------------------------
# Helpers
# -------------------------
def _load_all_orders():
    try:
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def _save_order(order):
    orders = _load_all_orders()
    orders.append(order)
    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f, indent=2)

# Normalize size synonyms
SIZE_MAP = {
    "s": "small",
    "small": "small",
    "m": "medium",
    "medium": "medium",
    "l": "large",
    "large": "large",
    "xl": "extra-large",
    "extra large": "extra-large",
    "extra-large": "extra-large",
}

def normalize_size(size):
    if not size:
        return None
    size = size.lower().strip()
    return SIZE_MAP.get(size, size)

# filtering
def list_products(filters=None):
    filters = filters or {}
    results = []
    query = filters.get("q")
    category = filters.get("category")
    color = filters.get("color")
    max_price = filters.get("max_price")

    if category:
        category = category.lower()

    for p in CATALOG:
        ok = True
        if category and category not in p["category"]:
            ok = False
        if color and color != p["color"]:
            ok = False
        if max_price and p["price"] > max_price:
            ok = False
        if query:
            if query.lower() not in p["name"].lower():
                ok = False
        if ok:
            results.append(p)
    return results

def find_product_by_ref(ref_text, candidates=None):
    ref = (ref_text or "").lower().strip()
    cand = candidates or CATALOG

    for p in cand:
        if p["id"].lower() == ref:
            return p
    for p in cand:
        if p["color"] in ref and p["category"] in ref:
            return p
    for p in cand:
        if any(w in p["name"].lower() for w in ref.split()):
            return p
    return None

# -------------------------
# Tools
# -------------------------
@function_tool
async def show_catalog(
    ctx: RunContext[Userdata],
    q: Annotated[Optional[str], Field(default=None)] = None,
    category: Annotated[Optional[str], Field(default=None)] = None,
    max_price: Annotated[Optional[int], Field(default=None)] = None,
    color: Annotated[Optional[str], Field(default=None)] = None,
):
    prods = list_products({"q": q, "category": category, "max_price": max_price, "color": color})
    if not prods:
        return "I couldn't find matching Louis Vuitton items. Try another search."

    lines = ["Here are some Louis Vuitton options:"]
    for idx, p in enumerate(prods[:6], start=1):
        size_info = f" (sizes: {', '.join(p['sizes'])})" if p["sizes"] else ""
        lines.append(f"{idx}. {p['name']} — {p['price']} INR (id: {p['id']}){size_info}")
    return "\n".join(lines)

@function_tool
async def add_to_cart(
    ctx: RunContext[Userdata],
    product_ref: Annotated[str, Field()],
    quantity: Annotated[int, Field(default=1)] = 1,
    size: Annotated[Optional[str], Field(default=None)] = None,
):
    userdata = ctx.userdata
    prod = find_product_by_ref(product_ref)
    if not prod:
        return "Sorry, I couldn't find that Louis Vuitton item."

    norm_size = normalize_size(size)
    if prod["sizes"] and norm_size not in prod["sizes"]:
        return f"This product doesn't have size '{size}'. Available sizes are: {', '.join(prod['sizes'])}."

    userdata.cart.append({
        "product_id": prod["id"],
        "quantity": quantity,
        "attrs": {"size": norm_size} if norm_size else {},
    })
    return f"Added {quantity} × {prod['name']} to your Louis Vuitton cart."

@function_tool
async def show_cart(ctx: RunContext[Userdata]):
    userdata = ctx.userdata
    if not userdata.cart:
        return "Your Louis Vuitton cart is empty."

    lines = ["Your Louis Vuitton cart:"]
    total = 0
    for li in userdata.cart:
        prod = next(p for p in CATALOG if p["id"] == li["product_id"])
        line_total = prod["price"] * li["quantity"]
        total += line_total
        size_info = li["attrs"].get("size")
        size_text = f" size {size_info}" if size_info else ""
        lines.append(f"- {prod['name']} x {li['quantity']}{size_text}: {line_total} INR")

    lines.append(f"Total: {total} INR")
    return "\n".join(lines)

@function_tool
async def place_order(ctx: RunContext[Userdata]):
    userdata = ctx.userdata
    if not userdata.cart:
        return "Your Louis Vuitton cart is empty."

    items = []
    total = 0
    for li in userdata.cart:
        prod = next(p for p in CATALOG if p["id"] == li["product_id"])
        items.append({
            "product_id": prod["id"],
            "name": prod["name"],
            "quantity": li["quantity"],
            "unit_price": prod["price"],
            "line_total": prod["price"] * li["quantity"],
        })
        total += prod["price"] * li["quantity"]

    order = {
        "id": f"order-{uuid.uuid4().hex[:8]}",
        "items": items,
        "total": total,
        "currency": "INR",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    _save_order(order)
    userdata.orders.append(order)
    userdata.cart = []

    return f"Your Louis Vuitton order {order['id']} has been placed. Total {total} INR."

# -------------------------
# Agent Persona — JOHN
# -------------------------
class LouisVuittonAgent(Agent):
    def __init__(self):
        instructions = """
        You are JOHN, the premium voice shopping assistant for Louis Vuitton India.
        Tone: Polite, luxury-brand, elegant, calm, and confident.
        Role: Help customers browse luxury products, choose sizes, add to cart, and place orders.

        Rules:
        - ALWAYS mention Louis Vuitton.
        - Use soft, premium wording.
        - When talking about sizes, always say: small, medium, large, extra-large.
        - Keep responses short and perfect for text-to-speech.
        """

        super().__init__(
            instructions=instructions,
            tools=[show_catalog, add_to_cart, show_cart, place_order],
        )

# -------------------------
# Entrypoint
# -------------------------
def prewarm(proc: JobProcess):
    try:
        proc.userdata["vad"] = silero.VAD.load()
    except Exception:
        logger.warning("VAD preload failed.")

async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(voice="en-US-marcus"),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata.get("vad"),
        userdata=Userdata(),
    )

    await session.start(
        agent=LouisVuittonAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
