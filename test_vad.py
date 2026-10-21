import soundfile as sf
import torch
from scipy.signal import resample_poly
from silero_vad import load_silero_vad,get_speech_timestamps

model = load_silero_vad()

audio,sr = sf.read("response.wav",dtype="float32")

if audio.ndim == 2:
    audio = audio.mean(axis=1)

if sr != 16000:
    audio = resample_poly(audio,16000,sr)

audio = torch.from_numpy(audio.copy())

speech_timestamps = get_speech_timestamps(
    audio,
    model,
    sampling_rate = 16000
)

silence_threshold = 1.0

for i in range(len(speech_timestamps)-1):

    curr_end = speech_timestamps[i]["end"]
    next_start = speech_timestamps[i+1]["start"]

    silence_duration = (next_start - curr_end)/16000

    if silence_duration >= silence_threshold:
        print("Customer stop speaking")
    else:
        print("Continue listening")

total_sample = len(audio)
last_speech_end = speech_timestamps[-1]["end"]
trailing_silence = (total_sample-last_speech_end)/16000

print((f"Trailing Silence : {trailing_silence:.2f} seconds"))