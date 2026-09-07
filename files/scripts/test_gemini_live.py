"""
Quick test: Verifies your Gemini API key works with the Live API.
Run this BEFORE wiring up Exotel.

Usage:
    pip install websockets
    GEMINI_API_KEY=your_key python test_gemini_live.py
"""

import asyncio
import json
import os
import sys
import base64
import websockets

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from dotenv import load_dotenv
    # Load from the backend folder relative to the script location
    load_dotenv(os.path.join(os.path.dirname(__file__), "../backend/.env"))
except ImportError:
    pass

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_google_ai_studio_api_key_here":
    raise SystemExit("Set GEMINI_API_KEY environment variable (or populate backend/.env) first!")

# Use the stable native audio model
MODEL = "gemini-2.5-flash-native-audio-latest"
WS_URL = (
    f"wss://generativelanguage.googleapis.com/ws/"
    f"google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
    f"?key={GEMINI_API_KEY}"
)


async def test_text_turn():
    """Send a text message and get back an audio response — confirms the connection works."""
    print(f"\n🔌 Connecting to Gemini Live API...")
    print(f"   Model: {MODEL}")

    async with websockets.connect(WS_URL) as ws:
        # Step 1: Send setup
        setup = {
            "setup": {
                "model": f"models/{MODEL}",
                "generation_config": {
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {"voice_name": "Aoede"}
                        }
                    },
                },
                "system_instruction": {
                    "parts": [{"text": "You are a helpful assistant. Keep responses brief."}]
                },
                "output_audio_transcription": {},
            }
        }
        await ws.send(json.dumps(setup))
        print("✅ Setup message sent")

        # Step 2: Wait for setup_complete
        resp = await ws.recv()
        data = json.loads(resp)
        if "setupComplete" in data:
            print("✅ Setup complete! Connection working.")
        else:
            print(f"⚠️  Unexpected response: {data}")
            return

        # Step 3: Send a text input turn
        text_msg = {
            "client_content": {
                "turns": [{
                    "role": "user",
                    "parts": [{"text": "Say hello in Hindi in one sentence."}]
                }],
                "turn_complete": True
            }
        }
        await ws.send(json.dumps(text_msg))
        print("✅ Text message sent: 'Say hello in Hindi in one sentence.'")
        print("\n📥 Receiving response...")

        # Step 4: Collect response
        audio_chunks = 0
        transcript   = ""
        async for message in ws:
            resp = json.loads(message)
            sc   = resp.get("serverContent", {})

            # Transcript
            if "outputTranscription" in sc:
                t = sc["outputTranscription"].get("text", "")
                if t:
                    transcript += t
                    print(f"   Transcript: {t}", end="", flush=True)

            # Audio chunks
            mt = sc.get("modelTurn", {})
            for part in mt.get("parts", []):
                if "inlineData" in part:
                    audio_chunks += 1

            # Turn complete
            if sc.get("turnComplete"):
                break

        print(f"\n\n✅ Response received!")
        print(f"   Audio chunks: {audio_chunks}")
        print(f"   Full transcript: {transcript or '(check outputTranscription config)'}")
        print(f"\n🎉 Gemini Live API is working correctly with your API key!")
        print(f"   You can now wire this up to Exotel telephony.\n")


async def test_sentiment_analysis():
    """Test the post-call sentiment analysis (uses standard Gemini API, not Live)."""
    import httpx
    print("\n🧪 Testing sentiment analysis...")

    sample_transcript = """
Customer: Hello?
Agent (Priya): Hello, this is Priya, an AI assistant calling from EduTech. Is this a good time?
Customer: Yes, what is this about?
Agent (Priya): I'm calling about our Data Science course. Are you interested in upskilling?
Customer: Actually yes, I've been thinking about this. Tell me more.
Agent (Priya): Great! Our course covers Python, ML, and real projects. Fee is ₹25,000 for 6 months.
Customer: That sounds interesting. Can someone call me back with details?
Agent (Priya): Absolutely! Our team will call you within 24 hours. Thank you!
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
Analyze this sales call and respond in JSON only:
{{"sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL", "summary": "2-sentence summary", "reason": "why this sentiment"}}

Transcript:
{sample_transcript}
"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        if resp.status_code == 200:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip().lstrip("```json").rstrip("```").strip()
            data = json.loads(text)
            print(f"✅ Sentiment: {data['sentiment']}")
            print(f"   Summary: {data['summary']}")
            print(f"   Reason: {data['reason']}")
        else:
            print(f"❌ Error: {resp.status_code} — {resp.text[:200]}")


if __name__ == "__main__":
    asyncio.run(test_text_turn())
    asyncio.run(test_sentiment_analysis())
