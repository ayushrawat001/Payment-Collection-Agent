import json
import torch
import numpy as np
import io
import asyncio
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException,Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from voice_agent import process_audio
from silero_vad import load_silero_vad
from scipy.io import wavfile
from fastapi.middleware.cors import CORSMiddleware


FFMPEG_PATH = r"C:\Users\AA\MediaGet2\ffmpeg.exe"
model = load_silero_vad()
VAD_CHUNK_SIZE = 512
model.reset_states()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "https://YOUR-VERCEL-DOMAIN.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

CUSTOMER_FILE = Path(__file__).parent/"temp_customers.json"

call_kpis= {}


@app.get("/api/customers/{cust_id}")
def get_customer(cust_id:str):
    with open(CUSTOMER_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    for customer in data["customers"]:
        if customer["id"] == cust_id:
            return customer

    raise HTTPException(
        status_code=404,
        detail="Customer Not Found"
    )

@app.post("/api/voice")
async def voice_endpoint(
    audio: UploadFile = File(...),
    cust_id: str = Form(...)
    ):
    try:
        audio_bytes = await audio.read()

        with open(CUSTOMER_FILE,"r",encoding="utf-8") as file:
            data = json.load(file)

        customer = None
        for item in data["customers"]:
            if item["id"] == cust_id:
                customer = item
                break

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer Not Found"
            )
        
        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="No audio received."
            )

        result = process_audio(
            audio_bytes,
            audio_extension=".webm",
            customer= customer,   
        )

        return result

    except HTTPException:
        raise

    except Exception as error:
        print("Voice agent error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Voice processing failed."
        )

@app.get("/api/kpi/{call_id}")
def get_kpi(call_id:str):
    kpis = call_kpis.get(call_id)

    if kpis is None:
        raise HTTPException(
            status_code=404,
            detail="Call KPI data not found"
        )
    return {
        "stt_avg": (
            sum(kpis["stt"]) / len(kpis["stt"])
            if kpis["stt"] else None
        ),
        "llm_avg": (
            sum(kpis["llm"]) / len(kpis["llm"])
            if kpis["llm"] else None
        ),
        "tts_avg": (
            sum(kpis["tts"]) / len(kpis["tts"])
            if kpis["tts"] else None
        ),
        "total_responses": kpis["total_responses"]
    }


@app.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket, cust_id:str):
    await websocket.accept()
    call_id = str(uuid.uuid4())

    call_kpis[call_id] = {
        "stt": [],
        "llm": [],
        "tts": [],
        "total_responses": 0
    }
    await websocket.send_json({
        "type": "call_started",
        "call_id": call_id
    })
    customer = get_customer(cust_id)
    audio_buffer = np.array([], dtype=np.float32)
    speech_started = False
    silence_chunks = 0
    SILENCE_LIMIT = 32
    utterance_buffer = []

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            if message.get("text") == "end_of_audio":
                break


            audio_chunk = message.get("bytes")

            if audio_chunk is None:
                continue
            pcm_samples = np.frombuffer(audio_chunk, dtype=np.int16)

            audio_float = pcm_samples.astype(np.float32) / 32768.0
            audio_buffer = np.concatenate((audio_buffer, audio_float))

            while len(audio_buffer) >= VAD_CHUNK_SIZE:
                vad_chunk = audio_buffer[:VAD_CHUNK_SIZE]
                audio_buffer = audio_buffer[VAD_CHUNK_SIZE:]

                audio_tensor = torch.from_numpy(vad_chunk.copy())
                speech_prob = model(audio_tensor, 16000).item()

                if speech_prob >= 0.3:
                    if not speech_started:
                        speech_started = True
                        print(speech_prob," audible")
                        await websocket.send_json({"type": "speech_started"})

                    silence_chunks = 0
                

               
                if speech_started:
                        utterance_buffer.append(vad_chunk)

                if speech_prob < 0.3 and speech_started:
                    silence_chunks += 1
                    print(speech_prob, "audible not")

                    if silence_chunks >= SILENCE_LIMIT:

                        utterance_audio = np.concatenate(utterance_buffer)
                        # Convert float32 audio to int16 PCM
                        audio_int16 = (np.clip(utterance_audio, -1, 1) * 32767).astype(np.int16)

                        # Write WAV audio into memory
                        wav_buffer = io.BytesIO()
                        wavfile.write(wav_buffer, 16000, audio_int16)

                        # Get WAV bytes for process_audio()
                        wav_bytes = wav_buffer.getvalue()
                        wav_buffer.close()

                        result = await asyncio.to_thread(
                            process_audio,
                            wav_bytes,
                            audio_extension=".wav",
                            customer=customer
                        )
                        if result is not None:
                            call_kpis[call_id]["stt"].append(result["latency"]["stt"])
                            call_kpis[call_id]["llm"].append(result["latency"]["llm"])
                            call_kpis[call_id]["tts"].append(result["latency"]["tts"])
                            call_kpis[call_id]["total_responses"] += 1
                            await websocket.send_json(result)

                        utterance_buffer = []
                        speech_started = False
                        silence_chunks = 0
                    


            # 16-bit PCM: each sample occupies 2 bytes
            if len(audio_chunk) % 2 != 0:
                print("Invalid PCM chunk: odd number of bytes")
                continue

            await websocket.send_text("chunk_received")

    except WebSocketDisconnect:
        print("Browser audio WebSocket disconnected")

app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)
