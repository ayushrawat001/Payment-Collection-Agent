import os
import base64
import tempfile
import time
from dotenv import load_dotenv
from sarvamai import SarvamAI
import datetime


load_dotenv()           



# Load generic payment policy
with open("generic_payment_policy.txt", "r", encoding="utf-8") as file:
    payment_policy = file.read()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)


def create_opening_message(customer):
    name = customer["name"]
    product = customer["product"]
    overdue_amount = customer.get("overdue_amt", 0)
    return (
        f"""नमस्ते {name} जी, मैं ABC Finance से payment collection assistant बोल रही हूँ। मैं आपके {product}के भुगतान के संबंध में कॉल कर रही हूँ। आपका बकाया भुगतान {overdue_amount} रुपये है। कृपया बताइए, आप भुगतान किस तारीख तक कर पाएँगे?"""
    )
def generate_opening_audio(customer):
    opening_message = create_opening_message(customer)

    tts_response = client.text_to_speech.convert(
        model="bulbul:v3",
        text=opening_message,
        language_code="hi-IN",
        speaker="ritu"
    )

    return {
        "answer": opening_message,
        "audio_base64": tts_response.audios[0],
        "audio_mime_type": "audio/wav"
    }

def generate_opening_audio(customer):
    opening_message = create_opening_message(customer)

    tts_response = client.text_to_speech.convert(
        model="bulbul:v3",
        text=opening_message,
        language_code="hi-IN",
        speaker="ritu"
    )

    return {
        "answer": opening_message,
        "audio_base64": tts_response.audios[0],
        "audio_mime_type": "audio/wav"
    }


def process_audio(audio_bytes, audio_extension=".webm",customer = None):

    messages = [
    {
        "role": "system",
        "content": f"""
        You are a female payment collection assistant for ABC Finance. Do not greet any customer.

        Company Policy:
        {payment_policy}

        Customer Details:
        {customer}
        Todat Date : {datetime.date.today()} read it in YYYY-MM-DD format.

        Conversation Rules:
        - Speak politely in Hindi.
        - You are making an outbound payment collection call.
        - Do not ask for the customer's ID; it is already available.
        - Ask one question at a time and wait for the customer's response.
        - Never invent customer details, payment amounts, or dates.
        - Distinguish total outstanding from overdue amount.
        - Answer the customer's actual question before continuing payment collection.
        - If user ask any thing that is regarding to date then read the due date in YYYY-MM-DD format.
        - If user denied for payment then tell to pay within the due date other wise company can take action accoring the company policy.
        - If customer promise to pay before due date just say thank you.
        - If customer say he/she is busy or say call them back then reply only Ok we will call you later.
        - If customer say why you disturb then say "sorry, I dont want to disturb you i just reminding you about your loan." in hindi
            """

    }
]
    
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
            stt_start = time.perf_counter()
            stt_response = client.speech_to_text.transcribe(
                file=audio_file,
                mode="transcribe",
                model="saaras:v4"
            )
        
        stt_latency = time.perf_counter() - stt_start
        print(f"STT latency: {stt_latency:.2f} seconds")

        customer_message = stt_response.transcript.strip()

        # 3. Generate the agent's text response
        messages.append({
            "role": "user",
            "content": f"""
                        Customer details:{customer}
                        Customer's message:{customer_message}
                        """
        })

        try:
            llm_start = time.perf_counter()
            llm_response = client.chat.completions(
                model="sarvam-105b-conversations",
                max_tokens=400,
                messages=messages
            )
            llm_latency = time.perf_counter() - llm_start
            print(f"LLM latency: {llm_latency:.2f} seconds")

            answer = llm_response.choices[0].message.content

            messages.append({
                "role": "assistant",
                "content": answer
            })

        except Exception:
            messages.pop()
            raise

        # 4. Generate speech from the answer
        tts_start = time.perf_counter()
        tts_response = client.text_to_speech.convert(
            model="bulbul:v3",
            text=answer,
            language_code="hi-IN",
            speaker="ritu"
        )
        tts_latency = time.perf_counter() - tts_start
        print(f"TTS latency: {tts_latency:.2f} seconds")

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
