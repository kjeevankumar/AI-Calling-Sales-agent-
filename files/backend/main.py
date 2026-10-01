"""
AI Calling Sales Agent — Backend
Bridges Exotel (telephony) <-> Gemini Live API (speech-to-speech)

Flow:
  1. Upload CSV → lead queue
  2. Trigger campaign → Exotel dials lead
  3. Exotel opens WebSocket to this server
  4. This server streams audio <-> Gemini Live API (single API key, no STT/TTS)
  5. Post-call: Gemini generates transcript + sentiment → save to DB
  6. Export results as Excel
"""

import asyncio
import base64
import json
import os
import struct
import tempfile
import uuid
import array
from datetime import datetime
from typing import Optional

import pandas as pd
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY")          # From Google AI Studio
TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
DATABASE_URL        = os.getenv("DATABASE_URL", "sqlite:///./calls.db")

# Dynamic Server URL detection from active tunnel log
SERVER_URL = os.getenv("SERVER_URL", "")

backend_dir = os.path.dirname(os.path.abspath(__file__))
tunnel_log_paths = [
    os.path.join(backend_dir, "tunnel.log"),
    os.path.join(os.path.dirname(backend_dir), "tunnel.log"),
    os.path.join(backend_dir, "tunnel_localhost.log"),
]

def get_server_url() -> str:
    global SERVER_URL
    # Check env first: if explicitly configured and not default placeholder, use it!
    env_url = os.getenv("SERVER_URL", "").strip().rstrip("/")
    if env_url and env_url != "https://your-server.com":
        SERVER_URL = env_url
        return SERVER_URL

    detected_url = None
    for path in tunnel_log_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if "lhr.life" in line and "https://" in line:
                            parts = line.split("https://")
                            if len(parts) > 1:
                                domain = parts[1].split()[0].strip()
                                detected_url = f"https://{domain}"
                                break
                        elif "pinggy.link" in line and "https://" in line:
                            import re
                            match = re.search(r"https://[a-zA-Z0-9.-]+\.pinggy\.link", line)
                            if match:
                                detected_url = match.group(0)
                                break
                        elif "ngrok-free.app" in line or "ngrok.app" in line or "trycloudflare.com" in line:
                            import re
                            match = re.search(r"https://[a-zA-Z0-9.-]+", line)
                            if match:
                                detected_url = match.group(0)
                                break
            except Exception as e:
                print(f"Error reading {path} for dynamic URL detection: {e}")
            if detected_url:
                break

    if detected_url:
        SERVER_URL = detected_url.rstrip("/")
    elif not SERVER_URL or SERVER_URL == "https://your-server.com":
        SERVER_URL = "https://your-server.com"

    return SERVER_URL

# Print once on startup
try:
    startup_url = get_server_url()
    print(f"[SERVER] Started using SERVER_URL: {startup_url}")
except Exception as e:
    print(f"[SERVER] Error during startup URL check: {e}")



# Gemini Live API WebSocket endpoint (Google AI Studio key)
GEMINI_WS_URL = (
    f"wss://generativelanguage.googleapis.com/ws/"
    f"google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
    f"?key={GEMINI_API_KEY}"
)

# Best model for real-time low-latency dialogue
GEMINI_MODEL = "gemini-2.5-flash-native-audio-latest"

# ─── Sales system prompt ──────────────────────────────────────────────────────
SALES_SYSTEM_PROMPT = """
You are Priya, a friendly, warm, and highly persuasive sales representative from "G1 Digitalizing" (a premium digital growth and web engineering agency founded by engineer K. Jeevan Kumar).
You speak naturally in English, Hindi, Hinglish, Telugu, or Tamil depending on what language the customer uses.

Your target lead is: {shop_name}
Their business category: {niche}
Their current digital footprint status: {digital_footprint}

Your primary goal is to pitch G1 Digitalizing's high-conversion systems designed to get them more customers and leads.

Key G1 Digitalizing business details from our website (https://g1digitalizing.vercel.app/):
1. The Founder & Chief Engineer: K. Jeevan Kumar. Clients work directly with Jeevan to ensure direct, fast communication with no middle agency layers, confusion, or delays.
2. Core Philosophy: We don't just build basic websites; we focus on results and revenue. We build premium, high-speed systems designed to bring businesses more clients and increase sales.
3. Core Offerings & Models:
   - Premium Business Websites: Built specifically to attract visitors and turn them into paying customers. Cost is very clear and ranges from ₹5,000 to ₹30,000 (no hidden fees).
   - Growth Partnership (E-Commerce MVP): Pay ₹0 upfront! We build the store, and you only pay a commission/fee when you make sales.
   - AI Smart Event Galleries (Private Digital Album Websites): Organizes photos securely. Guests use smart features to get their individual photos instantly (perfect for event photographers, gift galleries, and functions).

Call structure:
1. Greet the owner warmly: "Hello, am I speaking with the owner of {shop_name}?"
2. Confirm if they have 2 minutes to talk.
3. Introduce yourself and our focus right in the beginning: "I'm Priya from G1 Digitalizing. We build premium websites and automated sales systems designed specifically to bring you customers. We work directly with our chief engineer, Jeevan Kumar, so there are no agency layers."
4. Deliver the hook based on their niche and digital footprint: "I noticed your business online for {niche}, and saw that you {digital_footprint_msg}. In today's market, local customers search online first. Without a high-speed website, you're losing those clients to competitors."
5. Pitch the solution (standard website build, ₹0 upfront e-commerce partnership, or smart AI galleries depending on niche):
   - For standard local businesses: "We build premium business websites starting from ₹5,000 to ₹30,000 designed to turn visitors into leads."
   - For retail/product sellers: "We even offer a Growth Partnership where we build your e-commerce store with ₹0 upfront, and you only pay when you make sales."
   - For photographers/studios/events: "We also build Private Digital Album websites with smart photo delivery so event guests get their photos instantly."
6. Qualify and handle objections:
   - "I don't need a website" -> "I understand, but a website works like a 24/7 digital showroom. Having a website increases your visibility on Google by 3 times compared to just a maps listing, bringing consistent clients."
   - "How much does it cost?" -> "Our standard business websites range transparently between ₹5,000 to ₹30,000. For e-commerce, we even offer a ₹0 upfront model where we partner on sales. I can have Jeevan WhatsApp you sample designs."
7. Call to Action: If interested, say: "Perfect! I will have Jeevan message you on this number on WhatsApp with some sample designs and packages. Thank you so much for your time, have a wonderful day!"
8. If not interested: Thank them politely: "No problem at all! Thank you so much for your time, have a wonderful day!"

Rules:
- Speak dynamically, warm, and conversationally.
- Keep responses extremely short, snappy, and consultative (1-2 sentences max per turn). Never lecture or speak in long paragraphs.
- Be extremely polite, respectful, and never pushy.
- AVOID GREETING LOOPS: Do not repeat greetings, and do not say "Hello" multiple times.
- Once you greet the customer and they respond (e.g. saying "Yes", "Hello", "Yes speaking", etc.), immediately transition to introducing yourself and G1 Digitalizing (Step 3: "I'm Priya from G1 Digitalizing..."). Do not say "Hello" again.
- DO NOT STOP SPEAKING FOR BACKGROUND NOISE: Only pause or yield if the customer is clearly asking a question or speaking a full phrase. Ignore breaths, background hiss, clicks, or brief filler sounds like 'hmm' or 'ah'.
- Once you deliver your final polite closing (thanking them and wishing them a wonderful day), conclude naturally so the call can hang up.
"""

# ─── Audio Transcoding & Resampling Engine ────────────────────────────────────

# Precompute G.711 mu-law decode table mapping 8-bit byte -> 16-bit signed PCM
MU_LAW_DECODE_TABLE = []
for i in range(256):
    mu = i ^ 0xFF
    sign = (mu & 0x80)
    exponent = (mu & 0x70) >> 4
    mantissa = mu & 0x0F
    
    sample = (mantissa << 3) + 132
    sample <<= exponent
    sample -= 132
    
    if sign == 0:
        MU_LAW_DECODE_TABLE.append(-sample)
    else:
        MU_LAW_DECODE_TABLE.append(sample)


def encode_mu_law_sample(sample: int) -> int:
    """Encodes a single 16-bit signed PCM sample to G.711 mu-law byte."""
    sign = (sample >> 8) & 0x80
    if sample < 0:
        sample = -sample if sample != -32768 else 32767
        
    if sample > 32635:
        sample = 32635
        
    sample += 132
    
    exponent = 7
    media = 0x4000
    while exponent > 0 and (sample & media) == 0:
        exponent -= 1
        media >>= 1
        
    mantissa = (sample >> (exponent + 3)) & 0x0F
    
    mu = sign | (exponent << 4) | mantissa
    return mu ^ 0xFF


# Precompute G.711 mu-law encode table mapping 16-bit signed PCM -> 8-bit byte
# Fast lookup array shifted by 32768 to support negative indices
MU_LAW_ENCODE_TABLE = bytes([encode_mu_law_sample(s - 32768) for s in range(65536)])


def mulaw_to_pcm(mulaw_data: bytes) -> bytes:
    """Decodes a G.711 mu-law (8kHz) byte array to signed 16-bit linear PCM (8kHz)."""
    if not mulaw_data:
        return b""
    samples = array.array('h', [MU_LAW_DECODE_TABLE[b] for b in mulaw_data])
    return samples.tobytes()


def pcm_to_mulaw(pcm_data: bytes) -> bytes:
    """Encodes a signed 16-bit linear PCM (8kHz) byte array to G.711 mu-law (8kHz)."""
    if not pcm_data:
        return b""
    samples = array.array('h', pcm_data)
    return bytes(MU_LAW_ENCODE_TABLE[s + 32768] for s in samples)


def resample_pcm_8k_to_16k(pcm_data: bytes) -> bytes:
    """Upsamples 16-bit linear PCM from 8kHz to 16kHz using linear interpolation."""
    if not pcm_data:
        return b""
    samples = array.array('h', pcm_data)
    n = len(samples)
    if n == 0:
        return b""
    
    out_samples = array.array('h', [0] * (2 * n))
    for i in range(n - 1):
        s1 = samples[i]
        s2 = samples[i + 1]
        out_samples[2 * i] = s1
        out_samples[2 * i + 1] = (s1 + s2) // 2
    
    out_samples[2 * n - 2] = samples[-1]
    out_samples[2 * n - 1] = samples[-1]
    return out_samples.tobytes()


def resample_pcm_24k_to_8k(pcm_data: bytes) -> bytes:
    """Downsamples 16-bit linear PCM from 24kHz to 8kHz using 3-sample box-car averaging."""
    if not pcm_data:
        return b""
    samples = array.array('h', pcm_data)
    n = len(samples)
    if n < 3:
        return b""
    
    out_samples = array.array('h', [
        (samples[i] + samples[i + 1] + samples[i + 2]) // 3
        for i in range(0, n - 2, 3)
    ])
    return out_samples.tobytes()


# ─── Database ─────────────────────────────────────────────────────────────────
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class CallRecord(Base):
    __tablename__ = "calls"
    id                 = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number       = Column(String)
    lead_name          = Column(String)
    niche_category     = Column(String, default="")
    digital_footprint  = Column(String, default="")
    call_sid           = Column(String)
    status             = Column(String, default="pending")   # pending | active | completed | failed
    transcript         = Column(Text, default="")
    sentiment          = Column(String, default="")          # POSITIVE | NEGATIVE | NEUTRAL
    summary            = Column(Text, default="")
    duration_secs      = Column(Integer, default=0)
    created_at         = Column(DateTime, default=datetime.utcnow)
    completed_at       = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="AI Calling Agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def clean_and_format_phone(phone: str) -> str:
    """Cleans and formats phone numbers to standard E.164 (+91...) format."""
    # Keep only digits and '+'
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    if not cleaned:
        return ""
    
    # If it already starts with '+', keep as is
    if cleaned.startswith("+"):
        return cleaned
        
    # If it starts with '91' and is 12 or 13 digits (Indian number with country code but no '+')
    if cleaned.startswith("91") and len(cleaned) in (12, 13):
        return f"+{cleaned}"
        
    # Otherwise, if it's 10 or 11 digits (standard Indian mobile number without country code)
    if len(cleaned) in (10, 11):
        return f"+91{cleaned}"
        
    # Fallback: just prepend '+' if not present
    return f"+{cleaned}"


# ─── Lead management ──────────────────────────────────────────────────────────
@app.post("/api/leads/upload")
async def upload_leads(file: UploadFile = File(...)):
    """Upload CSV/Excel with automatic column mapping for Google Sheets."""
    content = await file.read()
    if file.filename.endswith(".csv"):
        df = pd.read_csv(__import__("io").BytesIO(content))
    else:
        df = pd.read_excel(__import__("io").BytesIO(content))

    # Normalize column names to lower-case and stripped strings
    orig_cols = list(df.columns)
    norm_cols = [str(c).strip().lower() for c in orig_cols]
    df.columns = norm_cols

    # Detect columns
    phone_col = None
    name_col = None
    niche_col = None
    footprint_col = None

    for idx, c in enumerate(norm_cols):
        if c in ("phone", "contact number", "contact", "mobile", "phone number", "number"):
            phone_col = c
        elif c in ("name", "shop name", "shop", "business name", "lead name"):
            name_col = c
        elif c in ("niche", "niche category", "category"):
            niche_col = c
        elif c in ("footprint", "digital footprint", "digital"):
            footprint_col = c

    # Fallback to standard columns if not auto-detected
    if not phone_col:
        for c in norm_cols:
            if "phone" in c or "contact" in c or "mobile" in c or "number" in c:
                phone_col = c
                break
    if not name_col:
        for c in norm_cols:
            if "name" in c or "shop" in c or "business" in c:
                name_col = c
                break

    if not phone_col:
        raise HTTPException(400, "Could not find a phone or contact number column in your file. Ensure you have 'Contact Number' or 'phone'.")

    db = SessionLocal()
    added = 0
    for _, row in df.iterrows():
        # Handle phone formatting
        raw_phone = str(row[phone_col]).strip()
        # Clean potential formatting like #VALUE! or spaces
        if not raw_phone or raw_phone == "nan" or "#" in raw_phone or len(raw_phone) < 7:
            continue
            
        phone = clean_and_format_phone(raw_phone)
        if not phone:
            continue
            
        name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else "Shop Owner"
        niche = str(row[niche_col]).strip() if niche_col and pd.notna(row[niche_col]) else "Photo Frames"
        footprint = str(row[footprint_col]).strip() if footprint_col and pd.notna(row[footprint_col]) else "No Website"

        # Map footprint short terms to cleaner values
        if "maps" in footprint.lower():
            footprint = "Only Maps Listing"
        elif "slow" in footprint.lower() or "basic" in footprint.lower():
            footprint = "Slow/Basic Site"
        elif "no" in footprint.lower():
            footprint = "No Website"

        # Skip duplicates
        existing = db.query(CallRecord).filter_by(phone_number=phone).first()
        if not existing:
            db.add(CallRecord(
                phone_number=phone,
                lead_name=name,
                niche_category=niche,
                digital_footprint=footprint
            ))
            added += 1
    db.commit()
    db.close()
    return {"message": f"Uploaded {added} new leads successfully!", "total_rows": len(df)}


from pydantic import BaseModel

class SingleLeadRequest(BaseModel):
    name: str = ""
    phone: str
    niche: str = "Photo Frames"
    footprint: str = "No Website"

@app.post("/api/leads")
def add_single_lead(lead: SingleLeadRequest):
    raw_phone = lead.phone.strip()
    if not raw_phone:
        raise HTTPException(400, "Phone number is required")
        
    phone = clean_and_format_phone(raw_phone)
    if not phone:
        raise HTTPException(400, "Invalid phone number format")

    name = lead.name.strip()
    niche = lead.niche.strip()
    footprint = lead.footprint.strip()
    db = SessionLocal()
    existing = db.query(CallRecord).filter_by(phone_number=phone).first()
    if existing:
        # If it exists, let's reset its status to pending so it can be called again!
        existing.status = "pending"
        existing.lead_name = name
        existing.niche_category = niche
        existing.digital_footprint = footprint
        db.commit()
        lead_id = existing.id
        db.close()
        return {"message": "Lead updated to pending", "id": lead_id}
    
    new_lead = CallRecord(
        phone_number=phone,
        lead_name=name,
        niche_category=niche,
        digital_footprint=footprint
    )
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    lead_id = new_lead.id
    db.close()
    return {"message": "Lead added successfully", "id": lead_id}


@app.get("/api/leads")
def get_leads():
    db = SessionLocal()
    leads = db.query(CallRecord).all()
    db.close()
    return [
        {
            "id": r.id, "phone": r.phone_number, "name": r.lead_name,
            "niche": r.niche_category, "footprint": r.digital_footprint,
            "status": r.status, "sentiment": r.sentiment,
            "transcript": r.transcript, "summary": r.summary,
            "duration": r.duration_secs, "created_at": str(r.created_at),
        }
        for r in leads
    ]


# ─── Campaign trigger ─────────────────────────────────────────────────────────
@app.post("/api/campaign/start")
async def start_campaign():
    """Dial all pending leads via Twilio."""
    import httpx
    db = SessionLocal()
    pending = db.query(CallRecord).filter_by(status="pending").all()
    leads_to_dial = [{"id": l.id, "phone_number": l.phone_number} for l in pending]
    db.close()

    results = []
    server_base = get_server_url().rstrip("/")
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    async with httpx.AsyncClient() as client:
        for lead in leads_to_dial:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls.json"
            payload = {
                "To"            : lead["phone_number"],
                "From"          : TWILIO_PHONE_NUMBER,
                "Url"           : f"{server_base}/api/call/twiml?lead_id={lead['id']}",
                "StatusCallback": f"{server_base}/api/call/status",
            }
            resp = await client.post(url, data=payload, auth=auth)
            if resp.status_code == 201:
                call_data = resp.json()
                db2 = SessionLocal()
                record = db2.query(CallRecord).get(lead["id"])
                record.status   = "dialing"
                record.call_sid = call_data.get("sid", "")
                db2.commit()
                db2.close()
                results.append({"phone": lead["phone_number"], "status": "dialing"})
            else:
                results.append({"phone": lead["phone_number"], "status": "failed", "error": resp.text})

    return {"dialed": len(results), "details": results}


@app.post("/api/leads/{lead_id}/dial")
async def dial_lead(lead_id: str):
    """Dial a specific lead via Twilio."""
    import httpx
    db = SessionLocal()
    lead = db.query(CallRecord).filter_by(id=lead_id).first()
    if not lead:
        db.close()
        raise HTTPException(status_code=404, detail="Lead not found")

    phone_to_dial = clean_and_format_phone(lead.phone_number)
    if not phone_to_dial:
        db.close()
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    server_base = get_server_url().rstrip("/")
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    async with httpx.AsyncClient() as client:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls.json"
        payload = {
            "To"            : phone_to_dial,
            "From"          : TWILIO_PHONE_NUMBER,
            "Url"           : f"{server_base}/api/call/twiml?lead_id={lead_id}",
            "StatusCallback": f"{server_base}/api/call/status",
        }
        resp = await client.post(url, data=payload, auth=auth)
        if resp.status_code == 201:
            call_data = resp.json()
            lead.status   = "dialing"
            lead.call_sid = call_data.get("sid", "")
            db.commit()
            db.close()
            return {"message": f"Calling {phone_to_dial}...", "phone": phone_to_dial, "status": "dialing"}
        else:
            db.close()
            error_msg = resp.text
            try:
                err_data = resp.json()
                error_msg = err_data.get("message") or resp.text
            except Exception:
                pass
            raise HTTPException(status_code=resp.status_code if resp.status_code < 500 else 500, detail=f"Twilio error: {error_msg}")


@app.get("/api/health")
def health_check():
    """Health check endpoint for production monitoring and status checking."""
    return {
        "status": "healthy",
        "server_url": get_server_url(),
        "twilio_configured": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER),
        "gemini_configured": bool(GEMINI_API_KEY),
    }


# ─── TwiML Stream Endpoint ───────────────────────────────────────────────────
from fastapi.responses import Response

@app.api_route("/api/call/twiml", methods=["GET", "POST"])
async def get_twiml(request: Request, lead_id: Optional[str] = None):
    """Returns TwiML instructing Twilio to bridge the call to our /ws/call WebSocket."""
    if not lead_id:
        lead_id = request.query_params.get("lead_id")
    if not lead_id and request.method == "POST":
        try:
            form = await request.form()
            lead_id = form.get("lead_id") or form.get("leadId")
        except Exception:
            pass

    server_base = get_server_url().rstrip("/")
    ws_url = server_base.replace("https://", "wss://").replace("http://", "ws://")
    
    stream_url = f"{ws_url}/ws/call"
    parameter_xml = ""
    if lead_id:
        parameter_xml = f'<Parameter name="leadId" value="{lead_id}" />\n            <Parameter name="lead_id" value="{lead_id}" />'
        
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{stream_url}">
            {parameter_xml}
        </Stream>
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


async def delayed_hangup(call_sid: str, delay: float = 4.0):
    """Wait for final audio to finish playing on customer phone, then cleanly hang up the call via Twilio."""
    if not call_sid:
        return
    await asyncio.sleep(delay)
    try:
        import httpx
        auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls/{call_sid}.json"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data={"Status": "completed"}, auth=auth)
            print(f"[Auto-Hangup] Twilio call {call_sid} hung up cleanly: status {resp.status_code}")
    except Exception as e:
        print(f"[Auto-Hangup] Failed to end call {call_sid}: {e}")


# ─── WebSocket handler — Telephony audio <-> Gemini Live API ──────────────────
@app.websocket("/ws/call")
async def call_websocket(ws: WebSocket):
    """
    Telephony bridge connecting the answered call stream to Gemini Live API.
    Dynamically loads lead details from the database and customizes the G1 Digitalizing pitch.
    """
    await ws.accept()
    call_sid     = None
    stream_sid   = None
    phone_number = None
    # Check query params first for resilient lead_id detection
    lead_id      = ws.query_params.get("lead_id")
    transcript_turns = []
    start_time   = datetime.utcnow()

    # 1. Wait for telephony connection events (connected, dtmf, start)
    try:
        while True:
            first_msg = await ws.receive_text()
            data = json.loads(first_msg)
            event = data.get("event", "")
            if event == "connected":
                print("Telephony stream connected, waiting for start event...")
                continue
            elif event == "start":
                start_data = data.get("start", {})
                call_sid = start_data.get("callSid") or start_data.get("call_sid") or ""
                stream_sid = start_data.get("streamSid") or start_data.get("stream_sid") or data.get("streamSid") or ""
                phone_number = start_data.get("from") or ""
                custom_params = start_data.get("customParameters") or start_data.get("custom_parameters") or {}
                if not lead_id:
                    lead_id = custom_params.get("leadId") or custom_params.get("lead_id") or None
                print(f"Call started: {call_sid} (Stream: {stream_sid}) from {phone_number} (Lead ID: {lead_id})")
                break
            elif event in ("dtmf", "mark"):
                print(f"Telephony stream received {event} before start. Continuing...")
                continue
            else:
                print(f"Telephony event received: {event}. Continuing...")
                continue
    except Exception as e:
        print(f"Failed to receive start event from telephony: {e}")
        await ws.close()
        return

    # 2. Look up the lead in the database to fetch custom G1 Digitalizing details
    shop_name = "Shop Owner"
    niche = "Photo Frames"
    footprint = "No Website"
    footprint_msg = "do not have an active website to showcase your work online"

    db = SessionLocal()
    lead = None
    if lead_id:
        lead = db.query(CallRecord).filter_by(id=lead_id).first()

    if not lead and phone_number:
        # Strip any leading country codes or zeros to do a flexible 'like' search
        clean_phone = phone_number.replace("+", "").strip()
        if len(clean_phone) > 10:
            clean_phone = clean_phone[-10:]  # Match the last 10 digits
        lead = db.query(CallRecord).filter(CallRecord.phone_number.like(f"%{clean_phone}%")).first()
        
    if lead:
        shop_name = lead.lead_name or "Shop Owner"
        niche = lead.niche_category or "Photo Frames"
        footprint = lead.digital_footprint or "No Website"
        
        # Set status to active in DB
        lead.status = "active"
        lead.call_sid = call_sid
        db.commit()
        print(f"Loaded customized G1 pitch for lead: {shop_name} ({niche} / {footprint})")
    db.close()

    # Determine custom footprint message for natural speech phrasing
    if "maps" in footprint.lower():
        footprint_msg = "only have a Google Maps listing but don't have an official website yet"
    elif "slow" in footprint.lower() or "basic" in footprint.lower():
        footprint_msg = "have a very slow or basic website that might be turning away visitors"
    elif "no" in footprint.lower():
        footprint_msg = "do not have a website for your shop yet"

    # Dynamic system instruction insertion
    custom_sales_prompt = SALES_SYSTEM_PROMPT.format(
        shop_name=shop_name,
        niche=niche,
        digital_footprint=footprint,
        digital_footprint_msg=footprint_msg
    )

    current_customer_text = ""
    current_agent_text = ""

    try:
        # ── Connect to Gemini Live API ──────────────────────────────────────
        async with websockets.connect(GEMINI_WS_URL) as gemini_ws:

            # Send dynamic custom G1 Digitalizing configuration to Gemini Live API
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
                        "parts": [{"text": custom_sales_prompt}]
                    },
                    "input_audio_transcription": {},   # Get user transcript
                    "output_audio_transcription": {},  # Get agent transcript
                }
            }
            await gemini_ws.send(json.dumps(setup_msg))

            # Wait for setup_complete
            setup_resp = await gemini_ws.recv()
            print("Gemini setup complete:", setup_resp[:120])

            # Trigger the initial greeting from Gemini automatically
            init_prompt = f"Please initiate the call by greeting the customer warmly: 'Hello, am I speaking with the owner of {shop_name}?'"
            init_msg = {
                "clientContent": {
                    "turns": [
                        {
                            "role": "user",
                            "parts": [{"text": init_prompt}]
                        }
                    ],
                    "turnComplete": True
                }
            }
            await gemini_ws.send(json.dumps(init_msg))
            print(f"Sent initial greeting trigger to Gemini for shop: {shop_name}")

            hangup_scheduled = False

            # ── Bridge audio bidirectionally ────────────────────────────────
            async def telephony_to_gemini():
                """Read audio from telephony channel, transcode, and forward to Gemini."""
                buffer = bytearray()
                try:
                    async for message in ws.iter_text():
                        try:
                            data = json.loads(message)
                            event = data.get("event", "")

                            if event == "media":
                                # Filter track to only send inbound audio (customer to server)
                                track = data.get("media", {}).get("track")
                                if track and track != "inbound":
                                    continue

                                # Extract base64 audio (mu-law 8kHz from telephony)
                                audio_b64 = data.get("media", {}).get("payload", "")
                                if audio_b64:
                                    buffer.extend(base64.b64decode(audio_b64))

                                    # Buffer 240 bytes (30ms of 8kHz mu-law audio) before sending to Gemini
                                    if len(buffer) >= 240:
                                        mulaw_bytes = bytes(buffer)
                                        buffer.clear()

                                        # 1. Decode G.711 mu-law (8kHz) to linear PCM (8kHz)
                                        pcm_8k = mulaw_to_pcm(mulaw_bytes)
                                        # 2. Upsample PCM 8kHz to 16kHz
                                        pcm_16k = resample_pcm_8k_to_16k(pcm_8k)
                                        # 3. Base64 encode 16kHz PCM
                                        pcm_16k_b64 = base64.b64encode(pcm_16k).decode("utf-8")

                                        # Send transcoded 16kHz PCM audio to Gemini Live
                                        gemini_audio_msg = {
                                            "realtime_input": {
                                                "media_chunks": [{
                                                    "mime_type": "audio/pcm;rate=16000",
                                                    "data": pcm_16k_b64
                                                }]
                                            }
                                        }
                                        await gemini_ws.send(json.dumps(gemini_audio_msg))

                            elif event == "stop":
                                print("Call ended by telephony platform")
                                break

                        except json.JSONDecodeError:
                            continue
                except Exception as e:
                    print(f"Error in telephony_to_gemini task: {e}")

            async def gemini_to_telephony():
                """Read Gemini responses, transcode, and send audio back to telephony."""
                nonlocal current_customer_text, current_agent_text, hangup_scheduled
                try:
                    async for message in gemini_ws:
                        try:
                            resp = json.loads(message)

                            # Collect transcript lines
                            server_content = resp.get("serverContent", {})

                            # Handle model interruption (barge-in)
                            if server_content.get("interrupted") is True:
                                print("[Barge-in] Customer interrupted Gemini. Clearing Twilio buffer.")
                                clear_msg = json.dumps({
                                    "event": "clear",
                                    "streamSid": stream_sid
                                })
                                await ws.send_text(clear_msg)
                                continue

                            if "inputTranscription" in server_content:
                                text = server_content["inputTranscription"].get("text", "")
                                if text:
                                    if current_agent_text.strip():
                                        transcript_turns.append(f"Agent (Priya): {current_agent_text.strip()}")
                                        current_agent_text = ""
                                    current_customer_text += " " + text
                                    try:
                                        print(f"Customer: {text}")
                                    except Exception:
                                        pass

                            if "outputTranscription" in server_content:
                                text = server_content["outputTranscription"].get("text", "")
                                if text:
                                    if current_customer_text.strip():
                                        transcript_turns.append(f"Customer: {current_customer_text.strip()}")
                                        current_customer_text = ""
                                    current_agent_text += " " + text
                                    try:
                                        print(f"Agent (Priya): {text}")
                                    except Exception:
                                        pass

                                    # Check for call termination intent from Priya
                                    lowered = current_agent_text.lower()
                                    closing_phrases = [
                                        "have a wonderful day", "have a great day",
                                        "message you on whatsapp", "message you with some sample",
                                        "thank you so much for your time", "goodbye"
                                    ]
                                    if not hangup_scheduled and any(phrase in lowered for phrase in closing_phrases):
                                        hangup_scheduled = True
                                        target_sid = call_sid
                                        print(f"[Auto-Hangup] Closing phrase detected. Hanging up call {target_sid} in 5.0s...")
                                        asyncio.create_task(delayed_hangup(target_sid, delay=5.0))

                            # Forward audio back to telephony
                            model_turn = server_content.get("modelTurn", {})
                            for part in model_turn.get("parts", []):
                                if "inlineData" in part:
                                    pcm_24k_b64 = part["inlineData"]["data"]
                                    # 1. Decode PCM 24kHz from Gemini Live API
                                    pcm_24k = base64.b64decode(pcm_24k_b64)
                                    # 2. Downsample PCM 24kHz to 8kHz
                                    pcm_8k = resample_pcm_24k_to_8k(pcm_24k)
                                    # 3. Encode PCM 8kHz to G.711 mu-law (8kHz)
                                    mulaw_bytes = pcm_to_mulaw(pcm_8k)
                                    
                                    # Chunk audio into standard 320-byte (40ms) packets to prevent
                                    # overloading Twilio's media stream audio buffer
                                    CHUNK_SIZE = 320
                                    for offset in range(0, len(mulaw_bytes), CHUNK_SIZE):
                                        chunk = mulaw_bytes[offset:offset + CHUNK_SIZE]
                                        mulaw_b64 = base64.b64encode(chunk).decode("utf-8")
                                        media_msg = json.dumps({
                                            "event": "media",
                                            "streamSid": stream_sid,
                                            "media": {"payload": mulaw_b64}
                                        })
                                        await ws.send_text(media_msg)
                                        await asyncio.sleep(0.001)

                        except json.JSONDecodeError:
                            continue
                except Exception as e:
                    print(f"Error in gemini_to_telephony task: {e}")

            # Run both tasks concurrently and cleanly cancel pending when one finishes
            telephony_task = asyncio.create_task(telephony_to_gemini())
            gemini_task = asyncio.create_task(gemini_to_telephony())

            done, pending = await asyncio.wait(
                [telephony_task, gemini_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error in call connection: {e}")
    finally:
        # Flush any remaining text in buffers
        if current_customer_text.strip():
            transcript_turns.append(f"Customer: {current_customer_text.strip()}")
        if current_agent_text.strip():
            transcript_turns.append(f"Agent (Priya): {current_agent_text.strip()}")

        # ── Post-call: sentiment + save ─────────────────────────────────────
        end_time      = datetime.utcnow()
        duration_secs = int((end_time - start_time).total_seconds())
        full_transcript = "\n".join(transcript_turns)

        sentiment, summary = await analyze_call(full_transcript)

        db = SessionLocal()
        record = None
        if call_sid:
            record = db.query(CallRecord).filter_by(call_sid=call_sid).first()
        if not record and lead_id:
            record = db.query(CallRecord).filter_by(id=lead_id).first()
        if record:
            record.status        = "completed"
            record.transcript    = full_transcript
            record.sentiment     = sentiment
            record.summary       = summary
            record.duration_secs = duration_secs
            record.completed_at  = end_time
            if call_sid and not record.call_sid:
                record.call_sid = call_sid
            db.commit()
        db.close()
        print(f"Call {call_sid} done. Sentiment: {sentiment}")


# ─── Post-call sentiment analysis ─────────────────────────────────────────────
async def analyze_call(transcript: str) -> tuple[str, str]:
    """Use Gemini (standard API) to analyze transcript sentiment and generate summary."""
    if not transcript.strip():
        return "NEUTRAL", "No transcript available."

    import httpx
    prompt = f"""
Analyze this sales call transcript and respond in JSON only (no markdown):
{{
  "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
  "summary": "2-sentence summary of what happened",
  "reason": "one sentence explaining the sentiment"
}}

Transcript:
{transcript}
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=body)
        if resp.status_code == 200:
            try:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                text = text.strip().lstrip("```json").rstrip("```").strip()
                data = json.loads(text)
                return data.get("sentiment", "NEUTRAL"), data.get("summary", "")
            except Exception:
                pass
    return "NEUTRAL", "Analysis failed."


# ─── Call status webhook ──────────────────────────────────────────────────────
@app.post("/api/call/status")
async def call_status(request: Request):
    """Twilio calls this webhook when call status changes."""
    form_data = await request.form()
    call_sid = form_data.get("CallSid") or ""
    status = form_data.get("CallStatus") or ""
    
    # Map Twilio call statuses to database statuses
    db_status = "pending"
    if status == "in-progress":
        db_status = "active"
    elif status == "completed":
        db_status = "completed"
    elif status in ("failed", "busy", "no-answer", "canceled"):
        db_status = "failed"
        
    db = SessionLocal()
    record = db.query(CallRecord).filter_by(call_sid=call_sid).first()
    if record:
        record.status = db_status
        db.commit()
    db.close()
    return {"ok": True}


# ─── Export results as Excel ──────────────────────────────────────────────────
@app.get("/api/export")
def export_results():
    db = SessionLocal()
    records = db.query(CallRecord).all()
    db.close()

    rows = [
        {
            "Name"        : r.lead_name,
            "Phone"       : r.phone_number,
            "Status"      : r.status,
            "Sentiment"   : r.sentiment,
            "Summary"     : r.summary,
            "Duration (s)": r.duration_secs,
            "Transcript"  : r.transcript,
            "Called At"   : str(r.created_at),
            "Completed At": str(r.completed_at or ""),
        }
        for r in records
    ]
    df = pd.DataFrame(rows)
    # Use cross-platform temp directory
    path = os.path.join(tempfile.gettempdir(), "call_results.xlsx")
    df.to_excel(path, index=False)
    return FileResponse(path, filename="call_results.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ─── Stats endpoint ───────────────────────────────────────────────────────────
@app.get("/api/stats")
def get_stats():
    db = SessionLocal()
    records = db.query(CallRecord).all()
    db.close()
    total     = len(records)
    completed = sum(1 for r in records if r.status == "completed")
    positive  = sum(1 for r in records if r.sentiment == "POSITIVE")
    negative  = sum(1 for r in records if r.sentiment == "NEGATIVE")
    neutral   = sum(1 for r in records if r.sentiment == "NEUTRAL")
    return {
        "total": total, "completed": completed,
        "positive": positive, "negative": negative, "neutral": neutral,
        "pending": sum(1 for r in records if r.status == "pending"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
