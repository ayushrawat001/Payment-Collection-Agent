import json
import torch
import numpy as np
import io
import asyncio
import uuid
import time
import threading
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException,Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from voice_agent import (
    process_audio,
    generate_opening_audio,
    transcribe_audio,
    classify_identity,
    generate_speech_response,
    stream_speech_response
)
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
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://localhost:8000",
        "https://payment-collection-agent.vercel.app",
        "https://payment-collection-agent-6w0qi9plg-ayushrawat001s-projects.vercel.app"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


CUSTOMER_FILE = Path(__file__).parent/"temp_customers.json"

call_kpis= {}

async def stream_tts_background(websocket, answer, call_id, send_lock, stop_event):

    loop = asyncio.get_running_loop()
    tts_start = time.perf_counter()

    async def send_audio_chunk(chunk):
        async with send_lock:
            await websocket.send_bytes(chunk)

    def generate_and_send():
        for chunk in stream_speech_response(answer):

            if stop_event.is_set():
                break

            future = asyncio.run_coroutine_threadsafe(
                send_audio_chunk(chunk),
                loop
            )
            future.result()

    try:
        await asyncio.to_thread(generate_and_send)

        # If the customer interrupted, don't mark the stream as completed
        if stop_event.is_set():
            return

        tts_latency = time.perf_counter() - tts_start

        call_kpis[call_id]["tts"].append(tts_latency)

        async with send_lock:
            await websocket.send_json({
                "type": "agent_audio_end",
                "tts_latency": tts_latency
            })
    except Exception as error:
        print("Streaming TTS error:", repr(error))

        if not stop_event.is_set():
            try:
                async with send_lock:
                    await websocket.send_json({
                        "type": "agent_audio_error"
                    })
            except Exception:
                pass


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

@app.get("/api/customers")
def get_all_customers():
    try:
        with open(CUSTOMER_FILE,"r", encoding="utf-8") as file:
            data = json.load(file)
        customers = data.get("customers",[])
        if not isinstance(customers, list):
            raise HTTPException(
                status_code=500,
                detail="Invalid customer data format."
            )

        return {
            "customers": customers,
            "total": len(customers)
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Customer data file not found."
        )
    
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Customer data file contains invalid JSON."
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
    }


@app.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket, cust_id:str):
    await websocket.accept()
    send_lock = asyncio.Lock()
    active_tts_stop = None
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
    identity_verified = False
    identity_uncertain_count = 0
    audio_buffer = np.array([], dtype=np.float32)
    speech_started = False
    silence_chunks = 0
    SILENCE_LIMIT = 32
    utterance_buffer = []

    try:
        opening_result = await asyncio.to_thread(
            generate_opening_audio,
            customer
        )

        await websocket.send_json({
            "type": "agent_message",
            **opening_result
        })

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

                if speech_prob >= 0.5:
                    if not speech_started:
                        speech_started = True
                        print(speech_prob," audible")
                        if active_tts_stop is not None:
                            active_tts_stop.set()
                        async with send_lock:
                            await websocket.send_json({"type": "speech_started"})       

                    silence_chunks = 0
                

               
                if speech_started:
                        utterance_buffer.append(vad_chunk)

                if speech_prob < 0.5 and speech_started:
                    silence_chunks += 1
                    print(speech_prob, "audible not")

                    if silence_chunks >= SILENCE_LIMIT:

                        utterance_audio = np.concatenate(utterance_buffer)
                        utterance_buffer = []
                        speech_started = False
                        silence_chunks = 0
                        # Convert float32 audio to int16 PCM
                        audio_int16 = (np.clip(utterance_audio, -1, 1) * 32767).astype(np.int16)

                        # Write WAV audio into memory
                        wav_buffer = io.BytesIO()
                        wavfile.write(wav_buffer, 16000, audio_int16)

                        # Get WAV bytes for process_audio()
                        wav_bytes = wav_buffer.getvalue()
                        wav_buffer.close()

                        
                        if not identity_verified:
                            customer_message = await asyncio.to_thread(
                                transcribe_audio,
                                wav_bytes,
                                ".wav"
                            )

                            if not customer_message:
                                utterance_buffer = []
                                speech_started = False
                                silence_chunks = 0
                                continue

                            identity_result = await asyncio.to_thread(
                                classify_identity,
                                customer_message
                            )

                            async with send_lock:
                                await websocket.send_json({
                                    "type": "customer_transcript",
                                    "transcript": customer_message
                                })
                            print("Identity result:", identity_result)

                            if identity_result == "true":
        
                                identity_verified = True
                                opening_text = f"""धन्यवाद जी, मैं आपके {customer["product"]} के बकाया भुगतान के संबंध में जानकारी देने के लिए कॉल कर रही हूँ। कृपया बताइए कि आप अपना {customer["overdue_amt"]} कब तक चुका देंगे? """
                                opening_result = await asyncio.to_thread(
                                    generate_speech_response,
                                    opening_text
                                )
                                async with send_lock:
                                    await websocket.send_json({
                                        "type": "agent_message",
                                        **opening_result
                                    })

                                utterance_buffer = []
                                speech_started = False
                                silence_chunks = 0


                            elif identity_result == "false":
                                closing_text = "कोई बात नहीं जी, असुविधा के लिए क्षमा चाहती हूँ। आपका दिन शुभ हो।"

                                closing_result = await asyncio.to_thread(
                                    generate_speech_response,
                                    closing_text
                                )

                                async with send_lock:
                                    await websocket.send_json({
                                        "type": "agent_message",
                                        **closing_result
                                    })
                                break

                            else:
                                identity_uncertain_count += 1

                                if identity_uncertain_count == 1:
                                    opening_result = await asyncio.to_thread(
                                        generate_opening_audio,
                                        customer
                                    )

                                    async with send_lock:
                                        await websocket.send_json({
                                            "type": "agent_message",
                                            **opening_result
                                        })
                                else:
                                    retry_text = (
                                        f"माफ़ कीजिए, क्या आप {customer.get('name', 'ग्राहक')} "
                                        "बोल रहे हैं? कृपया हाँ या नहीं में बताइए।"
                                    )


                                    closing_result = await asyncio.to_thread(
                                        generate_speech_response,
                                        retry_text
                                    )

                                    async with send_lock:
                                        await websocket.send_json({
                                            "type": "agent_message",
                                            **closing_result
                                        })
                                    break
                                utterance_buffer = []
                                speech_started = False
                                silence_chunks = 0

                            continue


                        result = await asyncio.to_thread(
                            process_audio,
                            wav_bytes,
                            audio_extension=".wav",
                            customer=customer,
                            stream_tts=True
                        )

                        if result is not None:
                            call_kpis[call_id]["stt"].append(result["latency"]["stt"])
                            call_kpis[call_id]["llm"].append(result["latency"]["llm"])
                            call_kpis[call_id]["total_responses"] += 1

                            # Send transcript and text response first
                            async with send_lock:
                                await websocket.send_json({
                                    "type": "agent_response",
                                    **result
                                })

                            # Start TTS generation in the background
                            active_tts_stop = threading.Event()

                            tts_task = asyncio.create_task(
                                stream_tts_background(
                                    websocket,
                                    result["answer"],
                                    call_id,
                                    send_lock,
                                    active_tts_stop
                                )
                            )

                        utterance_buffer = []
                        speech_started = False
                        silence_chunks = 0
                    


            # 16-bit PCM: each sample occupies 2 bytes
            if len(audio_chunk) % 2 != 0:
                print("Invalid PCM chunk: odd number of bytes")
                continue
            async with send_lock:
                await websocket.send_text("chunk_received")

    except WebSocketDisconnect:
        print("Browser audio WebSocket disconnected")

    finally:
        if active_tts_stop is not None:
            active_tts_stop.set()

app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)
