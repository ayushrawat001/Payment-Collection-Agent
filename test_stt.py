import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

response = client.speech_to_text.transcribe(
    file = open("test_audio.m4a", "rb"),
    model = "saaras:v4",
    mode = "transcribe"
)

print(response.transcript)