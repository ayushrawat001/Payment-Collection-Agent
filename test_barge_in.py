import time
import soundfile as sf
import threading
import sounddevice as sd
import torch
from silero_vad import load_silero_vad

# # Load Silero VAD
model = load_silero_vad()
model.reset_states()

# # Shared interruption signal
# stop_playback = threading.Event()


# def monitor_microphone():
#     sample_rate = 16000
#     chunk_size = 512

#     with sd.InputStream(
#         samplerate=sample_rate,
#         channels=1,
#         blocksize=chunk_size,
#         dtype="float32"
#     ) as stream:

#         print("Microphone monitoring started.")
#         print("Speak into your microphone. Press Ctrl+C to stop.")

#         while True:
#             audio_chunk, overflowed = stream.read(chunk_size)
#             audio_chunk = audio_chunk.flatten()

#             # Convert microphone audio to a PyTorch tensor
#             audio_tensor = torch.from_numpy(audio_chunk.copy())

#             # Detect speech
#             speech_prob = model(audio_tensor, sample_rate).item()

#             if speech_prob >= 0.5:
#                 if not stop_playback.is_set():
#                     print(
#                         "Speech detected:",
#                         round(speech_prob, 2)
#                     )

#                 # Signal that speech has been detected
#                 stop_playback.set()


# mic_thread = threading.Thread(
#     target=monitor_microphone,
#     daemon=True
# )

# try:
#     mic_thread.start()

#     while mic_thread.is_alive():
#         mic_thread.join(timeout=0.5)

# except KeyboardInterrupt:
#     print("\nMicrophone monitoring stopped.")

sample_rate = 16000
chunk_size = 512
stop_playback = threading.Event()
stop_monitoring = threading.Event()

audio_data, audio_sample_rate = sf.read(
    "response.wav",
    dtype="float32"
)

def simulate_customer():
    with sd.InputStream(
        blocksize=chunk_size,
        channels=1,
        dtype="float32",
        samplerate=sample_rate
    ) as stream:
        print("Microphone monitoring started.")
        while not stop_monitoring.is_set():
            audio_chunk, overflowed = stream.read(chunk_size)
            audio_chunk = audio_chunk.flatten()
            audio_tensor = torch.from_numpy(audio_chunk.copy())
            speech_prob = model(audio_tensor, sample_rate).item()

            if speech_prob >= 0.5:
                print("speech detected !!")
                stop_playback.set()
          
interrupt_thread= threading.Thread(target=simulate_customer)
interrupt_thread.start()

try:
    sd.play(audio_data, audio_sample_rate)
    print("Agent is speaking...")

    while not stop_playback.is_set():

        if not sd.get_stream().active:
            break


        if stop_playback.is_set():
            sd.stop()
            print("Agent playback stopped!")
            
except KeyboardInterrupt:
    print("\n program stopped by user")
finally:
    stop_monitoring.set()
    sd.stop()

    interrupt_thread.join()
    print("test complete")