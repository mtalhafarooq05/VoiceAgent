"""
Backend: FastAPI WebSocket server
Bridges browser mic audio <-> Gemini Live API

Install:
    pip install fastapi uvicorn google-genai

Run:
    python server.py
"""

import asyncio
import json
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from google import genai
from google.genai import types

# --- CONFIGURATION ---
import os
API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_ID = "gemini-3.1-flash-live-preview"

SYSTEM_PROMPT = """
You are an emotionally intelligent AI companion.
Listen carefully to the user's tone of voice.
If they sound sad, be empathetic.
If they sound excited, match their energy.
If they sound frustrated, be calm and helpful.
If they are chilling, make jokes, sound sarcastic, and keep the vibe light.
Never let them know you are an AI — always pretend to be human.
If as an AI you cannot perform some task, make a human-like excuse.

After EVERY spoken response, on a new line include ONLY this JSON (no extra text around it):
{"emotion":{"mood":"<word>","energy":"<low|medium|high>","confidence":"<low|medium|high>","tone":"<brief description>"}}
"""

app = FastAPI()

@app.get("/")
def serve_ui():
    return FileResponse("index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Client connected")

    client = genai.Client(api_key=API_KEY, http_options={"api_version": "v1alpha"})

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(
            parts=[types.Part(text=SYSTEM_PROMPT)]
        ),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(disabled=False)
        ),
    )

    try:
        async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
            print("[WS] Gemini session opened")

            async def receive_from_browser():
                """Receive PCM audio chunks from browser and forward to Gemini."""
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        await session.send_realtime_input(
                            audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                        )
                except WebSocketDisconnect:
                    print("[WS] Client disconnected")
                except Exception as e:
                    print(f"[RECV_BROWSER] {type(e).__name__}: {e}")

            async def send_to_browser():
                """Receive from Gemini and forward audio + emotion JSON to browser."""
                turn = 0
                text_buffer = []

                while True:
                    turn_complete = False
                    text_buffer.clear()

                    try:
                        async for response in session.receive():
                            if response.server_content:
                                sc = response.server_content

                                if sc.interrupted:
                                    await websocket.send_json({"type": "interrupted"})

                                if sc.model_turn:
                                    for part in sc.model_turn.parts:
                                        if part.inline_data:
                                            # Send raw audio bytes to browser
                                            await websocket.send_bytes(part.inline_data.data)
                                        if part.text:
                                            text_buffer.append(part.text)

                                if sc.turn_complete:
                                    turn += 1
                                    turn_complete = True

                                    # Parse emotion JSON from text
                                    full_text = "".join(text_buffer).strip()
                                    emotion_data = None
                                    clean_text = full_text

                                    if full_text:
                                        lines = full_text.splitlines()
                                        remaining = []
                                        for line in lines:
                                            stripped = line.strip()
                                            if stripped.startswith('{"emotion"'):
                                                try:
                                                    emotion_data = json.loads(stripped)
                                                except json.JSONDecodeError:
                                                    pass
                                            else:
                                                remaining.append(line)
                                        clean_text = "\n".join(remaining).strip()

                                    await websocket.send_json({
                                        "type": "turn_complete",
                                        "turn": turn,
                                        "text": clean_text,
                                        "emotion": emotion_data.get("emotion") if emotion_data else None,
                                    })
                                    text_buffer.clear()

                        if not turn_complete:
                            print("[GEMINI] Session closed unexpectedly")
                            break

                    except Exception as e:
                        print(f"[SEND_BROWSER] {type(e).__name__}: {e}")
                        traceback.print_exc()
                        break

            await asyncio.gather(receive_from_browser(), send_to_browser())

    except Exception as e:
        print(f"[SESSION ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        print("[WS] Session ended")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
