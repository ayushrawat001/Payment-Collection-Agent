import os
import base64
import tempfile
import json
from dotenv import load_dotenv
from sarvamai import SarvamAI


load_dotenv()



# Load generic payment policy
with open("generic_payment_policy.txt", "r", encoding="utf-8") as file:
    payment_policy = file.read()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)


messages = [
    {
        "role": "system",
        "content": f"""
        You are a polite payment collection assistant.

        Follow this company payment policy:
        {payment_policy}

        Use only the customer information provided in the conversation.
        Never invent payment amounts, due dates, or penalties.
        If customer information is missing, ask for clarification.
        Keep responses concise and conversational.
        """
    }
]


def process_audio(audio_bytes, audio_extension=".webm"):
    # 1. Save the browser's uploaded audio temporarily
    with tempfile.NamedTemporaryFile(
        suffix=audio_extension,
        delete=False
    ) as temp_audio:
        temp_audio.write(audio_bytes)
        audio_path = temp_audio.name

    try:
        # 2. Convert customer speech to text

        with open(audio_path, "rb") as audio_file:
            stt_response = client.speech_to_text.transcribe(
                file=audio_file,
                mode="transcribe",
                model="saaras:v4"
            )

        customer_message = stt_response.transcript.strip()

        # 3. Generate the agent's text response
        messages.append({
            "role": "user",
            "content": customer_message
        })

        try:
            llm_response = client.chat.completions(
                model="sarvam-105b-conversations",
                max_tokens=400,
                messages=messages
            )

            answer = llm_response.choices[0].message.content

            messages.append({
                "role": "assistant",
                "content": answer
            })

        except Exception:
            messages.pop()
            raise

        # 4. Generate speech from the answer
        tts_response = client.text_to_speech.convert(
            model="bulbul:v3",
            text=answer,
            language_code="en-IN",
            speaker="ritu"
        )

        audio_base64 = tts_response.audios[0]

        # 5. Return data to the webpage
        return {
            "transcript": customer_message,
            "answer": answer,
            "audio_base64": audio_base64,
            "audio_mime_type": "audio/wav"
        }

    finally:
        # 6. Delete the temporary audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
