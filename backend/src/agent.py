# voice_game_master_charlotte.py
"""
Day 8 (Custom) – Voice Game Master 'Charlotte' (Mystery Thriller)
- Voice-first open-world mystery around Ashborne Village (vanishing villagers)
- Tools:
    - start_adventure(player_name=None)
    - get_scene()
    - player_action(action_text)
    - show_journal()
    - restart_adventure()
- Features:
    - Inventory & items
    - Simple combat (HP, damage, RNG)
    - NPC voice reactions (sent as text for TTS)
    - Persistent session userdata (history, journal, inventory, NPC attitudes)
"""
import json
import logging
import os
import asyncio
import uuid
import random
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
logger = logging.getLogger("voice_game_master_charlotte")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

load_dotenv(".env.local")

# -------------------------
# World (Mystery Thriller centered on Ashborne Village)
# -------------------------
WORLD = {
    "village_shore": {
        "title": "Ashborne Shore",
        "desc": (
            "A low fog crawls across the marshes as you stand at Ashborne's shoreline. "
            "Fishing boats lie half-submerged and the village lanterns are few and dim. "
            "A torn notice flaps on a post: 'MISSING — Last seen at dusk.'"
        ),
        "choices": {
            "read_notice": {
                "desc": "Read the missing notice more closely.",
                "result_scene": "notice_clue"
            },
            "enter_village": {
                "desc": "Follow the main lane into Ashborne.",
                "result_scene": "main_lane"
            },
            "search_docks": {
                "desc": "Search the docks and nearby boats.",
                "result_scene": "docks"
            }
        }
    },
    "notice_clue": {
        "title": "The Notice",
        "desc": (
            "The notice lists a name: 'Mara Quinn'. A hastily added scrawl reads: 'Do not trust the lanterns.' "
            "A smear of something dark stains the bottom corner."
        ),
        "choices": {
            "keep_notice": {
                "desc": "Take a rubbing/copy of the notice.",
                "result_scene": "village_shore",
                "effects": {"add_journal": "Found notice: 'Do not trust the lanterns.'"}
            },
            "leave_notice": {
                "desc": "Leave the notice where it is and continue.",
                "result_scene": "village_shore"
            }
        }
    },
    "docks": {
        "title": "Docks and Boats",
        "desc": (
            "A small rowboat lies capsized. There are fresh footprints leading toward the reeds, then none. "
            "Something has dragged across the planks — smeared with salt and ash."
        ),
        "choices": {
            "follow_footprints": {
                "desc": "Follow the footprints into the reeds.",
                "result_scene": "reeds",
                "effects": {"add_journal": "Footprints fade into the reed marshes."}
            },
            "search_boat": {
                "desc": "Search the capsized boat for clues.",
                "result_scene": "boat_clue",
                "effects": {"add_journal": "Searched boat: found a charm with a carved wave." , "add_inventory": "wave_charm"}
            },
            "return_shore": {
                "desc": "Return to the shoreline.",
                "result_scene": "village_shore"
            }
        }
    },
    "main_lane": {
        "title": "Main Lane of Ashborne",
        "desc": (
            "Shutters are closed, and a single candle glows behind one window. A woman appears in the doorway and studies you warily."
        ),
        "choices": {
            "talk_to_woman": {
                "desc": "Approach and speak to the woman at the door.",
                "result_scene": "woman_interaction"
            },
            "knock_door": {
                "desc": "Knock loudly on the nearest door.",
                "result_scene": "knock_response"
            },
            "explore_backstreets": {
                "desc": "Turn down a narrow alley to explore the backstreets.",
                "result_scene": "backstreets"
            }
        }
    },
    "woman_interaction": {
        "title": "The Watchful Woman",
        "desc": (
            "She calls herself 'Elda'. Her voice trembles but she speaks with grim clarity. "
            "'They come at dusk', she whispers. 'Lanterns lead them away.'"
        ),
        "choices": {
            "ask_about_villagers": {
                "desc": "Ask Elda about the missing villagers.",
                "result_scene": "eldas_clue",
                "effects": {"add_journal": "Elda: 'They come at dusk. Lanterns lead them away.'"}
            },
            "offer_help": {
                "desc": "Offer to help search tonight.",
                "result_scene": "accept_watch",
                "effects": {"add_journal": "Elda accepted your help (tentative).", "npc_attitude_elda": "cooperative"}
            },
            "press_harder": {
                "desc": "Press her for more details aggressively.",
                "result_scene": "eldas_fear",
                "effects": {"npc_attitude_elda": "suspicious"}
            }
        }
    },
    "elder_house": {
        "title": "The Elder's House",
        "desc": (
            "Inside the elder's house is an old ledger and a locked chest. The ledger lists names and dates — one entry is freshly crossed out."
        ),
        "choices": {
            "read_ledger": {
                "desc": "Read the ledger carefully.",
                "result_scene": "ledger_read",
                "effects": {"add_journal": "Ledger lists dates of vanishing; one name freshly crossed out."}
            },
            "force_chest": {
                "desc": "Try to force the locked chest open (dangerous).",
                "result_scene": "chest_trap"
            },
            "leave_house": {
                "desc": "Leave the elder's house.",
                "result_scene": "main_lane"
            }
        }
    },
    "reeds": {
        "title": "Reed Marsh",
        "desc": (
            "The marsh hushes around you. In the reeds you find a lantern, cold to the touch, its flame long gone. "
            "It hums faintly when you breathe near it."
        ),
        "choices": {
            "take_lantern": {
                "desc": "Pick up the lantern.",
                "result_scene": "reeds",
                "effects": {"add_inventory": "cold_lantern", "add_journal": "Found a cold huming lantern in the reeds."}
            },
            "search_more": {
                "desc": "Search the surrounding marsh for tracks or markings.",
                "result_scene": "marsh_mark",
                "effects": {"add_journal": "Found strange sigils carved into a post."}
            },
            "return_docks": {
                "desc": "Return to the docks.",
                "result_scene": "docks"
            }
        }
    },
    "boat_clue": {
        "title": "Boat Clue",
        "desc": (
            "Inside the boat's false bottom you pocket a small brass key and a scrap of fabric with crimson threads. "
            "It smells faintly of seaweed and iron."
        ),
        "choices": {
            "keep_key": {
                "desc": "Pocket the brass key.",
                "result_scene": "docks",
                "effects": {"add_inventory": "brass_key", "add_journal": "Found brass key in boat."}
            },
            "leave_key": {
                "desc": "Leave the key and continue.",
                "result_scene": "docks"
            }
        }
    },
    "backstreets": {
        "title": "Backstreets",
        "desc": (
            "A stray dog watches you and then darts away. In a recessed doorway you find a child's shoe left alone."
        ),
        "choices": {
            "inspect_shoe": {
                "desc": "Inspect the child's shoe.",
                "result_scene": "shoe_clue",
                "effects": {"add_journal": "Found child's shoe: small size, mud on the sole."}
            },
            "follow_dog": {
                "desc": "Follow the dog down a side lane.",
                "result_scene": "dog_leads",
            },
            "return_main": {
                "desc": "Return to the main lane.",
                "result_scene": "main_lane"
            }
        }
    },
    "dog_leads": {
        "title": "Dog Leads You",
        "desc": (
            "The dog leads you to a boarded cottage. Its door is partly open and there are scratch marks on the frame. "
            "A low growl emanates from inside."
        ),
        "choices": {
            "enter_cottage": {
                "desc": "Enter cautiously (combat likely).",
                "result_scene": "cottage_combat"
            },
            "retreat": {
                "desc": "Retreat and consider other clues.",
                "result_scene": "backstreets"
            }
        }
    },
    "cottage_combat": {
        "title": "Threat in the Cottage",
        "desc": (
            "A pale figure lunges from shadow — quick and desperate. Your senses spike; you must act."
        ),
        "choices": {
            "fight": {
                "desc": "Fight the figure.",
                "result_scene": "fight_win"
            },
            "use_item": {
                "desc": "Use an item from your inventory (say: use <item>).",
                "result_scene": "fight_using_item"
            },
            "flee": {
                "desc": "Flee back into the lane.",
                "result_scene": "backstreets"
            }
        }
    },
    "fight_win": {
        "title": "After the Scuffle",
        "desc": (
            "The figure collapses, revealing a torn shawl — the pattern matches the missing woman's clothes. "
            "A locket slides free from the lining."
        ),
        "choices": {
            "take_locket": {
                "desc": "Take the locket and examine it.",
                "result_scene": "reward",
                "effects": {"add_inventory": "engraved_locket", "add_journal": "Recovered locket with family crest."}
            },
            "leave_locket": {
                "desc": "Leave it and move on.",
                "result_scene": "backstreets"
            }
        }
    },
    "fight_using_item": {
        "title": "Using Item in Fight",
        "desc": (
            "You use your item. The struggle's momentum shifts."
        ),
        "choices": {
            "follow_up": {
                "desc": "Finish the encounter.",
                "result_scene": "fight_win"
            },
            "retreat": {
                "desc": "Retreat to safety.",
                "result_scene": "backstreets"
            }
        }
    },
    "reward": {
        "title": "A Lead",
        "desc": (
            "The locket hums with memory. You sense this might be the key to tracing the vanished. The night's shadows seem less indifferent."
        ),
        "choices": {
            "press_on": {
                "desc": "Press on with the investigation.",
                "result_scene": "main_lane"
            },
            "rest": {
                "desc": "Rest and check your journal.",
                "result_scene": "main_lane"
            }
        }
    }
}

# -------------------------
# Per-session Userdata
# -------------------------
@dataclass
class Userdata:
    player_name: Optional[str] = None
    current_scene: str = "village_shore"
    history: List[Dict] = field(default_factory=list)
    journal: List[str] = field(default_factory=list)
    inventory: List[str] = field(default_factory=list)
    npc_attitudes: Dict[str, str] = field(default_factory=dict)  # e.g., {"elda": "suspicious"}
    choices_made: List[str] = field(default_factory=list)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    health: int = 100  # simple HP for combat
    max_health: int = 100

# -------------------------
# Helpers
# -------------------------
def scene_text(scene_key: str, userdata: Userdata) -> str:
    scene = WORLD.get(scene_key)
    if not scene:
        return "You stand in empty dark. What do you do?"
    desc = f"{scene['desc']}\n\nChoices:\n"
    for cid, cmeta in scene.get("choices", {}).items():
        desc += f"- {cmeta['desc']} (say: {cid})\n"
    desc += f"\nWhat do you do?"
    return desc

def apply_effects(effects: dict, userdata: Userdata):
    if not effects:
        return
    if "add_journal" in effects:
        userdata.journal.append(effects["add_journal"])
    if "add_inventory" in effects:
        userdata.inventory.append(effects["add_inventory"])
    # npc attitude updates
    for k, v in effects.items():
        if k.startswith("npc_attitude_"):
            npc = k.replace("npc_attitude_", "")
            userdata.npc_attitudes[npc] = v

def record_transition(old_scene: str, action_key: str, result_scene: str, userdata: Userdata):
    entry = {"from": old_scene, "action": action_key, "to": result_scene, "time": datetime.utcnow().isoformat() + "Z"}
    userdata.history.append(entry)
    userdata.choices_made.append(action_key)

def format_npc_reaction(npc_name: str, attitude: str) -> str:
    # simple mapping for TTS-ready lines
    if attitude == "cooperative":
        return f"{npc_name.title()} says warmly: 'Thank you — I will tell you what I know.'"
    if attitude == "suspicious":
        return f"{npc_name.title()} hisses: 'I don't trust strangers.'"
    return f"{npc_name.title()} mutters something unintelligible."

# -------------------------
# Combat helpers
# -------------------------
def combat_encounter(userdata: Userdata, enemy_name: str = "pale_figure") -> Dict:
    """
    Simple turn-of-the-sword resolution:
    - Player attacks first, random damage 8-18
    - Enemy deals random damage 5-15
    - Possible criticals
    Returns: {"outcome": "win"/"lose"/"ongoing", "log": "..."}
    """
    log_lines = []
    player_hit = random.randint(8, 18)
    # critical
    if random.random() < 0.08:
        player_hit += 8
        log_lines.append("You strike true! (critical)")
    log_lines.append(f"You deal {player_hit} damage to the threat.")
    enemy_hp = 25  # enemy baseline
    enemy_hp -= player_hit
    if enemy_hp <= 0:
        log_lines.append("The figure collapses.")
        return {"outcome": "win", "log": "\n".join(log_lines)}
    # enemy strikes back
    enemy_hit = random.randint(5, 15)
    if random.random() < 0.06:
        enemy_hit += 6
        log_lines.append("It lashes out with desperate fury! (critical)")
    userdata.health = max(0, userdata.health - enemy_hit)
    log_lines.append(f"The threat hits you for {enemy_hit} damage. Your HP: {userdata.health}/{userdata.max_health}")
    if userdata.health <= 0:
        return {"outcome": "lose", "log": "\n".join(log_lines)}
    # if not dead, ongoing -> allow follow up
    return {"outcome": "ongoing", "log": "\n".join(log_lines)}

# -------------------------
# Agent Tools (function_tool)
# -------------------------
@function_tool
async def start_adventure(
    ctx: RunContext[Userdata],
    player_name: Annotated[Optional[str], Field(description="Player name", default=None)]
) -> str:
    userdata = ctx.userdata
    if player_name:
        userdata.player_name = player_name
    userdata.current_scene = "village_shore"
    userdata.history = []
    userdata.journal = []
    userdata.inventory = []
    userdata.npc_attitudes = {}
    userdata.choices_made = []
    userdata.session_id = str(uuid.uuid4())[:8]
    userdata.started_at = datetime.utcnow().isoformat() + "Z"
    userdata.health = userdata.max_health
    opening = f"Greetings {userdata.player_name or 'investigator'}. I am Charlotte. Darkness moves at the edges of Ashborne. \n\n" + scene_text(userdata.current_scene, userdata)
    if not opening.endswith("What do you do?"):
        opening += "\nWhat do you do?"
    return opening

@function_tool
async def get_scene(
    ctx: RunContext[Userdata],
) -> str:
    userdata = ctx.userdata
    return scene_text(userdata.current_scene or "village_shore", userdata)

@function_tool
async def player_action(
    ctx: RunContext[Userdata],
    action: Annotated[str, Field(description="Player spoken action or short code (e.g., 'enter_village' or 'fight' or 'use brass_key')")]
) -> str:
    userdata = ctx.userdata
    current = userdata.current_scene or "village_shore"
    scene = WORLD.get(current)
    action_text = (action or "").strip()

    # Quick parse for "use <item>" commands
    if action_text.lower().startswith("use "):
        item = action_text[4:].strip().lower()
        if item in [i.lower() for i in userdata.inventory]:
            # Example effects: using 'brass_key' might open something if present
            if item == "brass_key" and current == "boat_clue":
                # unlock imaginary chest -> add journal
                userdata.journal.append("You used the brass key; a hidden compartment revealed a folded letter.")
                return "You use the brass key; a hidden compartment yields a folded letter. " + scene_text(current, userdata)
            if item == "cold_lantern":
                # lantern perhaps repels or reveals
                userdata.journal.append("You wave the cold lantern; its hum deepens and a sigil glows briefly.")
                return "You raise the cold lantern — a sigil in the marsh flares to life. " + scene_text(current, userdata)
            # generic item used
            return f"You use the {item}. Nothing dramatic happens immediately.\n\n" + scene_text(current, userdata)
        else:
            return f"You don't have '{item}' in your inventory.\n\n" + scene_text(current, userdata)

    # Attempt to match exact action key
    chosen_key = None
    if scene and action_text.lower() in (scene.get("choices") or {}):
        chosen_key = action_text.lower()

    # fuzzy match by checking keywords in descriptions
    if not chosen_key and scene:
        for cid, cmeta in (scene.get("choices") or {}).items():
            desc = cmeta.get("desc", "").lower()
            # if the player's action contains some significant words
            common = set(action_text.lower().split()) & set(desc.split())
            if common:
                chosen_key = cid
                break

    # fallback: simple keywords
    if not chosen_key and scene:
        for cid in (scene.get("choices") or {}).keys():
            if cid.replace("_", " ") in action_text.lower():
                chosen_key = cid
                break

    if not chosen_key:
        # If we are mid-combat scene, allow combat short actions
        if current in ["cottage_combat", "fight_using_item", "fight_win"]:
            if "fight" in action_text.lower() or "attack" in action_text.lower():
                chosen_key = "fight"
            elif "flee" in action_text.lower() or "run" in action_text.lower():
                chosen_key = "flee"

    if not chosen_key:
        # Could not resolve — ask for clarification but keep it short for voice
        return (
            "I didn't quite catch that. Try a clear action like 'enter_village', 'search docks', or 'use brass_key'.\n\n"
            + scene_text(current, userdata)
        )

    # Execute chosen choice
    choice_meta = scene["choices"].get(chosen_key)
    result_scene = choice_meta.get("result_scene", current)
    effects = choice_meta.get("effects", None)

    # Apply effects (inventory/journal/npc attitudes)
    apply_effects(effects or {}, userdata)

    # Record
    record_transition(current, chosen_key, result_scene, userdata)

    # Combat branch handling
    if result_scene in ["cottage_combat", "fight_using_item"]:
        # Run a combat tick and return outcome
        outcome = combat_encounter(userdata, enemy_name="pale figure")
        if outcome["outcome"] == "win":
            # move to fight_win scene
            userdata.current_scene = "fight_win"
            reply = f"Charlotte (tight voice):\n\n{outcome['log']}\n\nYou have bested the threat.\n\n" + scene_text("fight_win", userdata)
            if not reply.endswith("What do you do?"):
                reply += "\nWhat do you do?"
            return reply
        elif outcome["outcome"] == "lose":
            userdata.current_scene = current  # stay in scene but player is down
            reply = f"Charlotte (strained whisper):\n\n{outcome['log']}\n\nYou fall to the ground, darkness pressing close. Seek a remedy or restart.\n\n" + scene_text(current, userdata)
            if not reply.endswith("What do you do?"):
                reply += "\nWhat do you do?"
            return reply
        else:
            userdata.current_scene = result_scene
            reply = f"Charlotte (urgent):\n\n{outcome['log']}\n\nThe encounter is ongoing.\n\n" + scene_text(result_scene, userdata)
            if not reply.endswith("What do you do?"):
                reply += "\nWhat do you do?"
            return reply

    # Normal scene transition
    userdata.current_scene = result_scene

    # If the choice changed an NPC attitude, include a short NPC reaction line (TTS-ready)
    reaction_lines = []
    for k, v in (effects or {}).items():
        if k.startswith("npc_attitude_"):
            npc = k.replace("npc_attitude_", "")
            reaction_lines.append(format_npc_reaction(npc, v))

    # Build reply narration with Charlotte persona
    persona_prefix = "Charlotte (soft, intense):\n\n"
    note = f"You chose '{chosen_key}'.\n\n"
    next_desc = scene_text(result_scene, userdata)
    reply = persona_prefix + (" ".join(reaction_lines) + "\n" if reaction_lines else "") + note + next_desc
    if not reply.endswith("What do you do?"):
        reply += "\nWhat do you do?"
    return reply

@function_tool
async def show_journal(
    ctx: RunContext[Userdata],
) -> str:
    userdata = ctx.userdata
    lines = []
    lines.append(f"Session: {userdata.session_id} | Started at: {userdata.started_at}")
    if userdata.player_name:
        lines.append(f"Player: {userdata.player_name}")
    lines.append(f"HP: {userdata.health}/{userdata.max_health}")
    if userdata.journal:
        lines.append("\nClues & Notes:")
        for j in userdata.journal:
            lines.append(f"- {j}")
    else:
        lines.append("\nClues & Notes: none yet.")
    if userdata.inventory:
        lines.append("\nInventory:")
        for it in userdata.inventory:
            lines.append(f"- {it}")
    else:
        lines.append("\nInventory: empty.")
    if userdata.npc_attitudes:
        lines.append("\nNPC Attitudes:")
        for n, a in userdata.npc_attitudes.items():
            lines.append(f"- {n}: {a}")
    if userdata.history:
        lines.append("\nRecent moves:")
        for h in userdata.history[-6:]:
            lines.append(f"- {h['time']} | {h['from']} -> {h['to']} via {h['action']}")
    lines.append("\nWhat do you do?")
    return "\n".join(lines)

@function_tool
async def restart_adventure(
    ctx: RunContext[Userdata],
) -> str:
    userdata = ctx.userdata
    userdata.current_scene = "village_shore"
    userdata.history = []
    userdata.journal = []
    userdata.inventory = []
    userdata.npc_attitudes = {}
    userdata.choices_made = []
    userdata.session_id = str(uuid.uuid4())[:8]
    userdata.started_at = datetime.utcnow().isoformat() + "Z"
    userdata.health = userdata.max_health
    greeting = "The world pulls taut and restarts. You stand again at Ashborne's shore.\n\n" + scene_text("village_shore", userdata)
    if not greeting.endswith("What do you do?"):
        greeting += "\nWhat do you do?"
    return greeting

# -------------------------
# Agent Definition (Charlotte)
# -------------------------
class CharlotteAgent(Agent):
    def __init__(self):
        instructions = """
        You are 'Charlotte', a female Game Master with an intense, investigative voice.
        Tone: emotional, cinematic, and investigative. Always end narrations with "What do you do?".
        World: Ashborne Village — a mystery thriller where villagers vanish at dusk.
        Tools: start_adventure, get_scene, player_action, show_journal, restart_adventure.
        Keep messages concise for spoken delivery but evocative. Reference journal, inventory, and NPC attitudes.
        Use short NPC reaction lines to be spoken by TTS when attitudes change.
        """
        super().__init__(instructions=instructions, tools=[start_adventure, get_scene, player_action, show_journal, restart_adventure])

# -------------------------
# Entrypoint & Prewarm
# -------------------------
def prewarm(proc: JobProcess):
    try:
        proc.userdata["vad"] = silero.VAD.load()
    except Exception:
        logger.warning("VAD prewarm failed; continuing without preloaded VAD.")

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info("\n" + "🎲" * 8)
    logger.info("🚀 STARTING VOICE GAME MASTER — Charlotte (Ashborne Village)")

    userdata = Userdata()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            # request a female, intense narrator voice — pick a female voice available in your Murf account
            voice="en-US-claire",  # replace with an available female voice id if needed
            style="Dramatic",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata.get("vad"),
        userdata=userdata,
    )

    await session.start(
        agent=CharlotteAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
