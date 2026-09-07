import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_WS_URL = (
    f"wss://generativelanguage.googleapis.com/ws/"
    f"google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
    f"?key={GEMINI_API_KEY}"
)
GEMINI_MODEL = "gemini-2.5-flash-native-audio-latest"

async def test():
    try:
        print("Connecting to Gemini Live API...")
        print(f"URL: {GEMINI_WS_URL[:60]}... (key length: {len(GEMINI_API_KEY) if GEMINI_API_KEY else 0})")
        async with websockets.connect(GEMINI_WS_URL) as ws:
            setup_msg = {
                "setup": {
                    "model": f"models/{GEMINI_MODEL}",
                    "generation_config": {
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {"voice_name": "Aoede"}
                            }
                        },
                    },
                    "system_instruction": {
                        "parts": [{"text": "You are Priya from G1 Digitalizing."}]
                    },
                    "input_audio_transcription": {},
                    "output_audio_transcription": {},
                }
            }
            await ws.send(json.dumps(setup_msg))
            resp = await ws.recv()
            print("Success! Response:")
            print(resp[:500])
    except Exception as e:
        print("Error during test:", e)

asyncio.run(test())
