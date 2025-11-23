from dotenv import load_dotenv
load_dotenv(".env.local")

import importlib
import os
import sys

print("\n=== Checking Installed Dependencies ===")

packages_to_check = [
    "livekit",
    "livekit.agents",
    "livekit.plugins",
    "google.generativeai",
    "google.cloud.texttospeech",
    "deepgram",
    "murfai",
    "aiohttp",
    "numpy",
]

for pkg in packages_to_check:
    try:
        module = importlib.import_module(pkg)
        version = getattr(module, "__version__", "UNKNOWN")
        print(f"[ OK ] {pkg:35}  →  {version}")
    except Exception as e:
        print(f"[ MISSING ] {pkg:35}")

print("\n=== Checking Plugin Availability ===")

tests = {
    "deepgram.STT": "from livekit.plugins import deepgram",
    "murf.TTS": "from livekit.plugins import murf",
    "google.LLM": "from livekit.plugins import google",
    "silero.VAD": "from livekit.plugins import silero",
    "MultilingualModel": "from livekit.plugins.turn_detector.multilingual import MultilingualModel",
}

for name, code in tests.items():
    try:
        exec(code)
        print(f"[ OK ] {name}")
    except Exception as e:
        print(f"[ ERROR ] {name} → {type(e).__name__}: {e}")

print("\n=== Environment Variables ===")

envs = [
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "DEEPGRAM_API_KEY",
    "GOOGLE_API_KEY",
    "MURF_API_KEY",
]

for env in envs:
    print(f"{env} = {os.getenv(env)}")
print("\n=== Python Version ===")
print(sys.version)
