# Echo — Emotionally Intelligent Voice Companion

Real-time voice conversation with emotion detection, powered by Gemini Live.

## Requirements
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (only thing you need to install)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Setup

1. **Add your API key**
   ```bash
   cp .env.example .env
   # Open .env and replace "your_api_key_here" with your actual Gemini API key
   ```

2. **Build and run**
   ```bash
   docker compose up --build
   ```

3. **Open your browser**
   ```
   http://localhost:8000
   ```

4. **Tap the orb and start speaking.** Echo will reply and show an emotion analysis after each turn.

## Sharing with someone else

Send them the folder (zip it up). They only need Docker Desktop installed.
They add their own API key to `.env`, then run `docker compose up --build`.

## Stopping
```bash
docker compose down
```

## File structure
```
.
├── server.py          # FastAPI backend + Gemini Live bridge
├── index.html         # Frontend UI
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env               # Your API key (never share this)
└── .env.example       # Template for others
```
