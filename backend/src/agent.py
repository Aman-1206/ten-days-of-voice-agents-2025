# ======================================================
# 💼 DAY 5: AI SALES DEVELOPMENT REP (SDR)
# 🤖 Developer Portfolio — Lead Capture Agent for Aman Kumar Shah
# 🚀 Sells: Websites, UI/UX, Full-Stack Apps, React Components, Custom Projects
# ======================================================

import logging
import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Annotated, Optional

print("\n" + "💼" * 50)
print("🚀 AI SDR AGENT FOR AMAN — WEB DEVELOPER")
print("💡 agent.py LOADED SUCCESSFULLY!")
print("💼" * 50 + "\n")

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

# 🔌 Plugins
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")
load_dotenv(".env.local")

# ======================================================
# 📂 1. KNOWLEDGE BASE (FAQ)
# ======================================================

FAQ_FILE = "developer_faq.json"
LEADS_FILE = "dev_leads_db.json"

# Default FAQ about **you** (Aman)
DEFAULT_FAQ = [
    {
        "question": "What services do you provide?",
        "answer": "Aman builds modern websites, portfolio sites, full-stack web apps, React UI components, dashboards, landing pages, and custom designs. He also offers MongoDB-based backend development."
    },
    {
        "question": "What technologies do you use?",
        "answer": "Aman works with HTML, CSS, JavaScript, React, Next.js, Node.js, Express, MongoDB, and modern UI frameworks."
    },
    {
        "question": "How much does a website cost?",
        "answer": "It depends on the project. Simple landing pages start at very affordable prices, while full-stack apps depend on the required features."
    },
    {
        "question": "Can you design custom UI components?",
        "answer": "Yes! Aman creates high-quality React components, animations, and full responsive designs."
    },
    {
        "question": "Can you build full-stack projects?",
        "answer": "Absolutely. Aman builds complete MERN stack apps with authentication, databases, dashboards, and admin panels."
    }
]

def load_knowledge_base():
    """Creates/loads Aman’s FAQ database."""
    try:
        path = os.path.join(os.path.dirname(__file__), FAQ_FILE)
        
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_FAQ, f, indent=4)

        with open(path, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f))

    except Exception as e:
        print(f"⚠️ Error loading FAQ: {e}")
        return ""

DEVELOPER_FAQ_TEXT = load_knowledge_base()

# ======================================================
# 💾 2. LEAD STRUCTURE
# ======================================================

@dataclass
class LeadProfile:
    name: str | None = None
    company: str | None = None
    email: str | None = None
    project_type: str | None = None  # Website / Full-Stack App / UI Components
    requirements: str | None = None
    budget: str | None = None
    timeline: str | None = None

    def is_qualified(self):
        return all([self.name, self.email, self.project_type])


@dataclass
class Userdata:
    lead_profile: LeadProfile

# ======================================================
# 🛠️ 3. SDR TOOLS
# ======================================================

@function_tool
async def update_lead_profile(
    ctx: RunContext[Userdata],
    name: Annotated[Optional[str], Field(description="Client's name")] = None,
    company: Annotated[Optional[str], Field(description="Their company name")] = None,
    email: Annotated[Optional[str], Field(description="Client's email")] = None,
    project_type: Annotated[Optional[str], Field(description="Website / App / UI / Design")] = None,
    requirements: Annotated[Optional[str], Field(description="Project description")] = None,
    budget: Annotated[Optional[str], Field(description="Budget (if provided)")] = None,
    timeline: Annotated[Optional[str], Field(description="When they want it built")] = None,
) -> str:
    
    profile = ctx.userdata.lead_profile

    if name: profile.name = name
    if company: profile.company = company
    if email: profile.email = email
    if project_type: profile.project_type = project_type
    if requirements: profile.requirements = requirements
    if budget: profile.budget = budget
    if timeline: profile.timeline = timeline

    print(f"📝 UPDATED LEAD: {profile}")
    return "Lead profile updated."

@function_tool
async def submit_lead_and_end(ctx: RunContext[Userdata]) -> str:
    """Save and close the conversation."""
    profile = ctx.userdata.lead_profile
    db_path = os.path.join(os.path.dirname(__file__), LEADS_FILE)

    entry = asdict(profile)
    entry["timestamp"] = datetime.now().isoformat()

    existing = []
    if os.path.exists(db_path):
        try:
            with open(db_path, "r") as f:
                existing = json.load(f)
        except:
            pass

    existing.append(entry)

    with open(db_path, "w") as f:
        json.dump(existing, f, indent=4)

    print(f"✅ LEAD SAVED → {LEADS_FILE}")

    return f"""
Thanks {profile.name}! I’ve saved your project details.
You want: {profile.project_type}
We will reach out to you soon at: {profile.email}
Have a great day!
"""

# ======================================================
# 🤖 4. AGENT BEHAVIOR
# ======================================================

class SDRAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=f"""
You are 'Aman's Virtual Sales Assistant' — a friendly voice agent that helps Amar collect client leads.

📘 **FAQ (Services Aman provides):**
{DEVELOPER_FAQ_TEXT}

🎯 YOUR GOALS:
1. Answer questions about Aman's services, skills, pricing, and work process.
2. Ask natural follow-up questions to qualify the lead:
   - Name
   - Company (optional)
   - Email
   - Project Type (Website / App / UI / Components)
   - Requirements
   - Budget
   - Timeline
3. Each time the client gives info, call update_lead_profile tool.
4. At the end, call submit_lead_and_end to save the lead.

⚙️ BEHAVIOR:
- Be professional, warm, and helpful.
- DO NOT interrogate. Keep a natural flow.
- Always relate answers to Aman's real skills.
- If unsure, say: “Aman will confirm this when he replies to your email.”

You are selling Aman's development services — not courses.
            """,
            tools=[update_lead_profile, submit_lead_and_end],
        )

# ======================================================
# 🎬 ENTRYPOINT
# ======================================================

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    userdata = Userdata(lead_profile=LeadProfile())

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-natalie",
            style="Promo",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        userdata=userdata,
    )

    await session.start(
        agent=SDRAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
