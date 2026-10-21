import sounddevice as sd
import threading
import numpy as np
import torch
from silero_vad import load_silero_vad


# audio_data, sample_rate = sf.read("response.wav",dtype="")

# def stop_audio():
#     time.sleep(2)
#     sd.stop()
#     print("audio stopped")
# threading.Thread(target=stop_audio).start()

# sd.play(audio_data, sample_rate)

# sd.wait()

# def worker_task(name,delay):
#     print(f"thread {name} start")
#     time.sleep(delay)
#     print(f"thread {name} finished")

# t1 = threading.Thread(target=worker_task,args=("A",3))
# t2 = threading.Thread(target=worker_task,args=("B",1))

# t1.start()
# t2.start()

# t1.join()
# t2.join()

# print("both threads completed")

model = load_silero_vad()
model.reset_states()

stop_playback = threading.Event()

def monitot_microphone():

    sample_rate = 16000,
    chunk_size = 512
    with sd.InputStream(
        blocksize=chunk_size,
        channels=1,
        dtype="float32",
        samplerate=sample_rate
    ) as stream :

        print("Microphone monitoring started")
        while True:
            audio_chunk, overflowed = stream.read(512)
            audio_chunk = audio_chunk.flatten()

            audio_tensor = torch.from_numpy(audio_chunk.copy())
            speech_prob = model(audio_tensor,16000).item()

            if speech_prob >= 0.5:
                print("Speech detected : ", speech_prob)

mic_thread = threading.Thread(target=monitot_microphone)
mic_thread.start()

