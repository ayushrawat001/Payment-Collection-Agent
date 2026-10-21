import sounddevice as sd
import numpy as np
import torch
import soundfile as sf
import os
import base64
import time
import threading
import queue

from dotenv import load_dotenv
from sarvamai import SarvamAI
from silero_vad import load_silero_vad


model = load_silero_vad()
model.reset_states()

load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

sample_rate = 16000
chunk_size = 512
silence_limit = 32

audio_buffer = []
silence_chunks = 0
silence_detected = False
speech_started = False

stop_playback = threading.Event()
agent_speaking = threading.Event()
shutdown_event = threading.Event()
call_active = False
audio_queue = queue.Queue()

def monitor_microphone():
    audio_buffer = []
    silence_chunks = 0
    speech_started = False

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        blocksize=chunk_size,
        dtype="float32"
    ) as mic_stream:
        
        while not shutdown_event.is_set():
            audio_chunk, overflowed = mic_stream.read(chunk_size)
            audio_chunk = audio_chunk.flatten()

            audio_tensor = torch.from_numpy(audio_chunk.copy())
            speech_prob = model(audio_tensor, sample_rate).item()

            if speech_prob >= 0.5:
                if agent_speaking.is_set():
                    stop_playback.set()
                    sd.stop()

                speech_started = True
                silence_chunks = 0
                audio_buffer.append(audio_chunk.copy())

            elif speech_started:
                silence_chunks += 1
                audio_buffer.append(audio_chunk.copy())

                if silence_chunks >= silence_limit:
                    complete_audio = np.concatenate(audio_buffer)
                    audio_queue.put(complete_audio)

                    audio_buffer = []
                    silence_chunks = 0
                    speech_started = False
                    model.reset_states()

def conversation_worker():
    while not shutdown_event.is_set():
        complete_audio = audio_queue.get()

        print("Customer utterance received")
        start_time = time.perf_counter()

        sf.write(
            "customer_utterance.wav",
            complete_audio,
            sample_rate
        )

        with open("customer_utterance.wav", "rb") as audio_file:
            stt_response = client.speech_to_text.transcribe(
                file=audio_file,
                model="saaras:v4",
                mode="transcribe"
            )

        customer_message = stt_response.transcript.strip()
        if not customer_message:
            continue
        print(customer_message)
        messages.append({
            "role": "user",
            "content": customer_message
        })

        llm_response = client.chat.completions(
            model="sarvam-105b-conversations",
            messages=messages,
            max_tokens=200
        )

        llm_answer = llm_response.choices[0].message.content

        messages.append({
            "role": "assistant",
            "content": llm_answer
        })

        
        tts_response = client.text_to_speech.convert(
            text=llm_answer,
            model="bulbul:v3",
            language_code="hi-IN",
            speaker="ritu"
        )
    
        audio_bytes = base64.b64decode(tts_response.audios[0])

        with open("response.wav", "wb") as f:
            f.write(audio_bytes)

        audio_data, output_sample_rate = sf.read(
            "response.wav",
            dtype="float32"
        )

        total_latency = time.perf_counter() - start_time
        print("End-to-end latency:", total_latency)

        agent_speaking.set()
        stop_playback.clear()

        try:
            sd.play(audio_data, output_sample_rate)
            sd.wait()

            if stop_playback.is_set():
                print("Agent playback interrupted")
        finally:
            agent_speaking.clear()
            # stop_playback.clear()


messages=[
            {
                "role": "system",
                "content": """
                            You are a polite conversation model for normal chitchat.
                            Be polite and concise.
                            """
            }
        ]

def start_call():
        
        global call_active

        if call_active:
            return False

        shutdown_event.clear()
        stop_playback.clear()

        mic_thread = threading.Thread(
            target=monitor_microphone,
            daemon=True
        )

        worker_thread = threading.Thread(
            target=conversation_worker,
            daemon=True
        )

        mic_thread.start()
        worker_thread.start()
        call_active = True
        print("Voice agent started.")
        return True
        # mic_thread.join()
        # worker_thread.join()


def stop_call():
    global call_active
    call_active = False
    shutdown_event.set()
    stop_playback.set()
    sd.stop()
    print("Voice agent stopped.")