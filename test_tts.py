import os
import base64
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

response = client.text_to_speech.convert(
    text="Hello, I'm good what about you",
    language_code= "hi-IN",
    model="bulbul:v3",
    speaker="ritu"
)

audio_bytes = base64.b64decode(response.audios[0])

with open("audio.wav","wb") as f:
    f.write(audio_bytes)

print("Audio generated successfully")