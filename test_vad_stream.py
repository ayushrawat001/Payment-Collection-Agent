import soundfile as sf
import torch
from scipy.signal import resample_poly
from silero_vad import load_silero_vad

model = load_silero_vad()

audio, sr = sf.read("response.wav", dtype="float32")


if audio.ndim == 2:
    audio = audio.mean(axis=1)

if sr != 16000:
    audio = resample_poly(audio, 16000, sr)

audio = torch.from_numpy(audio.copy())

chunk_size = 512

silence_chunk = 0
silence_threshold = 1.0
silence_detected = False

for start in range(0,len(audio)-chunk_size+1,chunk_size):
    chunk = audio[start: start + chunk_size]
    speech_prob = model(chunk,16000).item()
    if speech_prob >= 0.5:
        print("Speech detected")    
        silence_chunk = 0
        silence_detected = False
    else:
        silence_chunk += 1
        silence_duration = silence_chunk * 512/16000
        if silence_duration >= silence_threshold:
            print("1 second of silence detected")
            silence_detected = True
        print("Silence detected")
