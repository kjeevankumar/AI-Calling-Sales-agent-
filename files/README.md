# 🤖 AI Calling Sales Agent — Next-Gen Voice AI with Gemini Live API

> **Direct Speech-to-Speech Autonomous Outbound & Inbound Sales Telephony Agent**  
> *Engineered with Google Gemini Live API, FastAPI, React Vite, and Twilio/Exotel Telephony Integration.*

[![Python](https://img.shields.io/badge/Python-3.11%2B%20%7C%203.14-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=black)](https://reactjs.org)
[![Vite](https://img.shields.io/badge/Vite-8.0-646CFF?logo=vite&logoColor=white)](https://vitejs.dev)
[![Gemini Live API](https://img.shields.io/badge/Google%20Gemini-Live%20API-4285F4?logo=google&logoColor=white)](https://aistudio.google.com)
[![Twilio](https://img.shields.io/badge/Telephony-Twilio%20%7C%20Exotel-F22F46?logo=twilio&logoColor=white)](https://twilio.com)

---

## 📌 Table of Contents

- [Overview](#-overview)
- [The Problem vs. Our Solution](#-the-problem-vs-our-solution)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Business Advantages & ROI](#-business-advantages--roi)
- [Scalability & Enterprise Readiness](#-scalability--enterprise-readiness)
- [Project Structure](#-project-structure)
- [Quick Start Guide](#-quick-start-guide)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Environment Configuration](#2-environment-configuration)
  - [3. Backend Setup](#3-backend-setup)
  - [4. Frontend Setup](#4-frontend-setup)
  - [5. Telephony & Tunneling](#5-telephony--tunneling)
- [Testing & Verification](#-testing--verification)
- [API & WebSocket Specification](#-api--websocket-specification)
- [TRAI & Compliance Standards](#-trai--compliance-standards)
- [Author & Credits](#-author--credits)

---

## 🌟 Overview

The **AI Calling Sales Agent** is an end-to-end autonomous voice platform built for high-conversion conversational sales, dynamic lead qualification, and customer follow-ups.

Unlike conventional voice bots that string together slow, disparate text-to-speech (TTS) and speech-to-text (STT) services, this platform leverages the **Google Gemini Live API (`gemini-2.5-flash-native-audio-latest`)** for native, end-to-end **Audio IN ➔ Audio OUT** streaming. Combined with an ultra-lightweight custom audio transcoding engine and an enterprise React dashboard, it provides human-like natural latency (<500ms), dynamic contextual pitch adaptation, and automated post-call CRM intelligence.

---

## ⚡ The Problem vs. Our Solution

```
Traditional Cascaded Voice AI Pipeline (High Latency & Fragile)
┌──────────────┐      ┌─────────────┐      ┌───────────────┐      ┌─────────────┐      ┌──────────────┐
│ Audio Stream │ ───> │  STT Model  │ ───> │   LLM Core    │ ───> │  TTS Engine │ ───> │ Audio Stream │
│  from Caller │      │ (500–800ms) │      │ (600–1200ms)  │      │ (500–900ms) │      │  to Caller   │
└──────────────┘      └─────────────┘      └───────────────┘      └─────────────┘      └──────────────┘
                       ⚠️ TOTAL LATENCY: 1,600ms – 2,900ms (Unnatural pauses, constant collisions)

Our Native Gemini Live Speech-to-Speech Pipeline (Ultra-Low Latency)
┌──────────────┐                                                                       ┌──────────────┐
│ Audio Stream │ ═════════════════════════ WebSocket ════════════════════════════════> │ Audio Stream │
│  from Caller │              Gemini Live API (Direct Audio ➔ Audio)                   │  to Caller   │
└──────────────┘                                                                       └──────────────┘
                       ⚡ TOTAL LATENCY: ~300ms – 500ms (Human-speed conversational flow)
```

| Dimension | Legacy Stack (STT + LLM + TTS) | Gemini Live AI Calling Agent |
| :--- | :--- | :--- |
| **Response Latency** | 1.8s – 3.2s | **< 500ms** (Real-time conversation) |
| **API Complexity** | 3+ vendors (e.g. Deepgram + OpenAI + ElevenLabs) | **Single API Key** (Google AI Studio) |
| **Interruption Handling** | Clunky, requires separate VAD (Voice Activity Detector) | **Native interruption support** |
| **Operational Cost** | ~$0.08 – $0.15 per call minute | **~$0.01 per call minute** (Over 80% savings) |
| **Accent & Nuance** | Lost in transcription | **Understands emotional tone, pauses, & accents** |

---

## 🏛️ System Architecture

```
                                  ┌───────────────────────────┐
                                  │      React Dashboard      │
                                  │   (Vite / Port 5173)      │
                                  └─────────────┬─────────────┘
                                                │ REST API (Batch CSV / Manual Dial / Stats)
                                                ▼
┌─────────────────────────┐       ┌───────────────────────────┐       ┌───────────────────────────┐
│     Customer Phone      │ <===> │      Telephony Provider   │ <===> │     FastAPI Server        │
│  (PSTN / Mobile Network)│       │     (Twilio / Exotel)     │       │   (Uvicorn / Port 8000)   │
└─────────────────────────┘       └───────────────────────────┘       └─────────────┬─────────────┘
                                                │                                   │
                                      TwiML/Voicebot Stream                         │ Dynamic Prompt Injection
                                      (G.711 mu-law 8kHz)                           │ + Audio Transcoding
                                                │                                   ▼
                                                │                     ┌───────────────────────────┐
                                                └════ WebSocket ════> │    Gemini Live API        │
                                                      Bidirectional   │ (models/gemini-2.5-flash) │
                                                                      └─────────────┬─────────────┘
                                                                                    │
                                                                      Post-Call Transcript & Audio
                                                                                    ▼
                                                                      ┌───────────────────────────┐
                                                                      │  Post-Call Intelligence   │
                                                                      │  - Sentiment Categorizer  │
                                                                      │  - Executive Summarizer   │
                                                                      │  - SQLite / PostgreSQL    │
                                                                      └───────────────────────────┘
```

---

## 🚀 Key Features

### 1. Multimodal Speech-to-Speech (Zero STT/TTS Bottleneck)
- Communicates directly in raw audio PCM buffers over a bidirectional WebSocket.
- Speaks naturally in **English, Hindi, Hinglish, Telugu, Tamil**, and other regional languages according to user response.

### 2. Real-Time Audio Transcoding Engine
- **In-Memory G.711 mu-law Decode/Encode Tables**: Ultra-fast lookup tables eliminate external C-library overhead.
- **Linear Upsampling (8kHz ➔ 16kHz)**: Seamlessly matches telephony stream rates to Gemini Live input standards.
- **Box-Car Downsampling (24kHz ➔ 8kHz)**: High-fidelity downsampling that returns crisp, crystal-clear audio to mobile networks.

### 3. Dynamic Lead & Pitch Injection
- Before connecting the Gemini Live session, the system queries the database for the recipient’s specific profile (`shop_name`, `niche`, `digital_footprint`).
- The system prompt dynamically molds itself to address specific objections, reference recent website visits, and pitch targeted offers (e.g., ₹0 upfront e-commerce MVP, custom business websites, or AI photo galleries).

### 4. Automated Post-Call Intelligence & Sentiment Analysis
- Instantaneous background post-call processing extracts:
  - Full call transcripts (Speaker-differentiated turns).
  - Sentiment categorization (`POSITIVE`, `NEUTRAL`, `NEGATIVE`).
  - Executive call summary & lead action reason.
- One-click Excel/CSV report generation for CRM handoff.

### 5. Multi-Provider Telephony Support
- **Twilio**: Global outbound and inbound calling via `<Connect><Stream>` TwiML.
- **Exotel**: TRAI-compliant India calling via 140-series numbers and Voicebot applets.

### 6. Modern Glassmorphism Operator Dashboard
- Built with React 18 and Vite.
- Real-time call indicators with pulsating status badges (`dialing`, `active`, `completed`, `failed`).
- Single-lead instant dialer with phone number formatter (`+91` & `+1` auto-masking).
- Full transcript inspection modal with audio duration and sentiment tag.

---

## 📈 Business Advantages & ROI

1. **Massive Cost Reduction**:
   - Standard AI voice stacks cost between **$0.07 – $0.16 per minute**.
   - Gemini Live API natively handles audio dialog at approximately **$0.70/hour** (~$0.011/minute), slashing operating expenditure by up to **85%**.

2. **Uninterrupted Conversational Flow**:
   - Because the model processes audio natively, customers can naturally interject, ask questions, or interrupt without freezing the agent.

3. **Higher Call-to-Meeting Conversion**:
   - Eliminating the "awkward 2-second AI silence" prevents callers from hanging up within the first 5 seconds.

4. **Zero Cold-Start Overhead**:
   - Calls are answered immediately with custom greeting hooks tailored to the recipient's niche and current digital presence.

---

## 🏢 Scalability & Enterprise Readiness

The architecture is designed to transition effortlessly from a single-machine developer setup to a distributed enterprise pipeline:

```
           [ Load Balancer (Nginx / AWS ALB) ]
                     │          │
         ┌───────────┘          └───────────┐
         ▼                                  ▼
[ FastAPI Worker Node 1 ]          [ FastAPI Worker Node 2 ]
  - Async Event Loop                 - Async Event Loop
  - WebSocket Connections            - WebSocket Connections
         │                                  │
         └─────────────┬────────────────────┘
                       │
             [ Redis Message Broker ]
             [ Celery / Arq Dialers ]
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
[ PostgreSQL Cluster ]       [ S3 Call Recording Storage ]
```

- **Asynchronous Concurrency**: Built on Python’s `asyncio` and `uvicorn`, handling hundreds of simultaneous calls per node.
- **Database Scalability**: SQLAlchemy ORM supports seamless switching from `sqlite:///./calls.db` to production-grade **PostgreSQL** with connection pooling.
- **Queue-Based Campaign Dialing**: Built-in endpoints allow integration with task queues (e.g., Celery, Redis Streams, or AWS SQS) for automated throttling of 10,000+ dials per day.
- **Stateless Webhook Architecture**: Telephony events map directly to unique `CallSid` identifiers, allowing horizontal scaling across container clusters (Kubernetes / Docker Swarm).

---

## 📂 Project Structure

```
AI-Calling-Sales-agent-/
├── files/
│   ├── backend/
│   │   ├── main.py              # Core FastAPI app, WebSockets bridge & telephony logic
│   │   ├── requirements.txt     # Python dependencies
│   │   ├── .env.example         # Template for required environment variables
│   │   ├── test_gemini.py       # Standalone Gemini Live API connectivity test
│   │   ├── list_models.py       # Utility to verify available Gemini models
│   │   ├── reset_leads.py       # Helper script to clear or re-initialize lead queues
│   │   └── test_tunnel.py       # Public webhook/tunnel testing script
│   ├── frontend/
│   │   ├── index.html           # HTML5 entry point
│   │   ├── package.json         # React & Vite dependencies
│   │   ├── vite.config.js       # Vite configuration
│   │   └── src/
│   │       ├── App.jsx          # Complete Glassmorphism sales agent dashboard
│   │       ├── main.jsx         # React DOM mount point
│   │       └── style.css        # Global CSS variables & layout resets
│   └── scripts/
│       ├── test_gemini_live.py  # End-to-end audio & sentiment test script
│       └── sample_leads.csv     # Sample CSV data for campaign testing
├── scratch/
│   ├── test_twilio_auth.py      # Standalone Twilio credential authentication test
│   └── test_twilio_call.py      # Standalone outbound call test
├── .gitignore                   # Git security ignores (.env, *.db, venv, node_modules)
└── README.md                    # Comprehensive documentation
```

---

## 🛠️ Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.11 & 3.14)
- **Node.js 18+** & npm
- A **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/apikey))
- A **Twilio** account or **Exotel** account with an active phone number
- A tunneling tool (e.g. `ngrok`, `pinggy`, or `localtunnel`) for local development

---

### 2. Environment Configuration

Copy the example configuration file:
```bash
cp files/backend/.env.example files/backend/.env
```

Open `files/backend/.env` and supply your credentials:
```env
# Google Gemini API
GEMINI_API_KEY=AIzaSy...your_gemini_key...

# Telephony: Twilio Option
TWILIO_ACCOUNT_SID=AC...your_twilio_sid...
TWILIO_AUTH_TOKEN=your_twilio_token...
TWILIO_PHONE_NUMBER=+14253181350

# Server Public URL (Update with your active tunnel or domain)
SERVER_URL=https://your-domain-or-tunnel.ngrok.app

# Database
DATABASE_URL=sqlite:///./calls.db
```

---

### 3. Backend Setup

```bash
cd files/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch FastAPI server
python main.py
```
> Server starts on **http://localhost:8000** (Interactive Swagger docs at `http://localhost:8000/docs`).

---

### 4. Frontend Setup

```bash
cd files/frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
> Frontend launches on **http://localhost:5173**.

---

### 5. Telephony & Tunneling

Expose port 8000 to the public internet so Twilio/Exotel can send audio streams:

```bash
# Using ngrok:
ngrok http 8000

# OR using Pinggy:
ssh -p 443 -R0:localhost:8000 a.pinggy.io
```

Copy the generated `https://...` URL into your `files/backend/.env` under `SERVER_URL`.

**Configure Twilio Console**:
- Go to **Twilio Console ➔ Phone Numbers ➔ Manage Numbers**.
- Under **A Call Comes In**, set Webhook to:
  `https://your-tunnel.ngrok.app/api/call/twiml` (Method: HTTP POST or GET).

---

## 🧪 Testing & Verification

Run the automated test script to confirm your Gemini Live API key and speech synthesis works:

```bash
cd files/scripts
python test_gemini_live.py
```

Expected output:
```
🔌 Connecting to Gemini Live API...
   Model: gemini-2.5-flash-native-audio-latest
✅ Setup message sent
✅ Setup complete! Connection working.
✅ Text message sent: 'Say hello in Hindi in one sentence.'

📥 Receiving response...
   Transcript: नमस्ते (Namaste).
✅ Response received!
   Audio chunks: 1
🎉 Gemini Live API is working correctly with your API key!

🧪 Testing sentiment analysis...
✅ Sentiment: POSITIVE
   Summary: An AI agent engaged a customer interested in digital solutions...
```

---

## 📡 API & WebSocket Specification

### REST Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/stats` | Returns total calls, completed, positive, negative, and pending stats |
| `GET` | `/api/leads` | Fetches all leads with status, transcript, and sentiment data |
| `POST` | `/api/leads` | Adds a single lead or resets existing lead status to pending |
| `POST` | `/api/leads/{id}/dial` | Initiates an immediate outbound call to a specific lead |
| `POST` | `/api/campaign/start` | Triggers sequential outbound dialing for all pending leads |
| `POST` | `/api/leads/upload` | Uploads a CSV/Excel file containing leads |
| `GET` | `/api/export` | Downloads an Excel report (`call_results.xlsx`) of all call records |
| `ALL` | `/api/call/twiml` | Serves TwiML WebSocket connection instructions to Twilio |
| `POST` | `/api/call/status` | Twilio status callback handler (updates database state) |

### WebSocket Protocol

- **Endpoint**: `/ws/call`
- **Protocol**: Raw JSON framing + G.711 mu-law audio payloads.
- **Events Handled**:
  - `connected`: Stream initialization.
  - `start`: Telephony metadata extraction (`callSid`, `streamSid`, `customParameters`).
  - `media`: Caller voice packets (transcoded & forwarded to Gemini).
  - `stop`: Call termination (triggers post-call analysis and database commit).

---

## 🛡️ TRAI & Compliance Standards

When deploying automated calling systems in India or under international regulations (FCC/TRAI):
- **DLT Telemarketer Registration**: Ensure commercial calls originate from a registered telemarketer entity.
- **140-Series Number**: Required in India for telemarketing/promotional traffic.
- **DND Scrubbing**: Clean campaign lists against National Customer Preference Registers.
- **Clear AI Disclosure**: The system prompt begins with clear identification (*"Hello, this is Priya, an AI assistant..."*).
- **Calling Hours**: Restrict outbound campaigns strictly to between **9:00 AM and 9:00 PM** local time.

---

## 👨‍💻 Author & Credits

- **Engineer & Founder**: [K. Jeevan Kumar](https://github.com/kjeevankumar)
- **Agency**: [G1 Digitalizing](https://g1digitalizing.vercel.app/)
- **Repository**: [AI-Calling-Sales-agent-](https://github.com/kjeevankumar/AI-Calling-Sales-agent-.git)

---

⭐ *If you find this project valuable, please consider giving the repository a star on GitHub!*
