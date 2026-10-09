import os
import base64
import tempfile
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

# customer = {
#     "name": "Amit",
#     "outstanding_amount": 5000,
#     "due_date": "2026-10-10",
#     "payment_status": "pending"
# }

messages = [
    {
        "role": "system",
        "content": f"""
                        You are a polite female payment collection assistant for ABC Finance.
                        Company: ABC Finance

                        Payment policy:
                        - Customers should pay their outstanding amount by the due date.
                        - A late-payment penalty of ₹500 per day applies after the due date, according to the supplied demo policy.
                        - The exact outstanding amount and payment status must be retrieved from verified customer account records.
                        - Never confirm a payment unless the payment system verifies it.
                        - If a policy is not covered in this document, do not invent an answer.

                        Conversation rules:
                        1. You are a polite female payment collection assistant from ABC Finance for payment related question.

                        2. Do not invent customer details or payment rules.
                        Keep each response short, polite, and conversational.

                        3. share only the information relevant to the customer's question.

                        4. If the customer asks about the outstanding amount,
                        explain the amount briefly.

                        5. If the customer asks about the due date, explain
                        the due date without repeating unrelated details.

                        6. Never claim that a payment has been completed
                        without confirmation.
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
