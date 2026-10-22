import os
import base64
import tempfile
import time
from dotenv import load_dotenv
from pathlib import Path
from sarvamai import SarvamAI
import datetime


load_dotenv()           


# Load generic payment policy


BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "generic_payment_policy.txt",
          "r", encoding="utf-8") as file:
    payment_policy = file.read()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

def create_opening_message(customer):
        name = customer["name"]
        return (
            f"""नमस्ते {name} जी, मैं ABC Finance से payment collection assistant बोल रही हूँ। मैं आपके Loan के भुगतान के संबंध में कॉल कर रही हूँ। """
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
        
                IF ques ask these or any question which indirectly means any of these give response in hindi as following instructions
                
                मेरे पास कौन-सा लोन है?
                Explain the customer's loan type using their customer record.
        
                मेरा कितना पैसा चुकाना बाकी है?
                Tell the customer the remaining outstanding amount using their customer record.
        
                मेरा कितना पेमेंट ओवरड्यू है?
                Tell the overdue amount.
        
                मुझे पेमेंट किस तारीख तक करना है?
                Tell the customer the due date from their customer record.
        
                अगर मैं ड्यू डेट तक पेमेंट नहीं कर पाया तो क्या होगा?
                Explain the applicable consequences according to company policy. Do not invent penalties, charges, or other consequences.
        
                मेरे पास अभी पैसे नहीं हैं, मैं क्या करूँ?
                Respond politely and empathetically. Explain only the payment options or assistance permitted by company policy.
        
                आप मुझे बार-बार कॉल करके परेशान क्यों करते हैं?
                Acknowledge the customer's concern respectfully and explain the purpose of the payment reminder without arguing or pressuring them.
        
                मैं अभी व्यस्त हूँ, क्या आप मुझे बाद में कॉल कर सकते हैं?
                Acknowledge the request and ask for a suitable callback date and time. Do not claim that a callback has been scheduled unless the system supports scheduling it.
        
                मैं ड्यू डेट से पहले पेमेंट कर दूँगा।
                Acknowledge the customer's commitment politely. Do not claim that payment has been received or verified.
        
                मैं अभी पेमेंट नहीं करना चाहता, आप क्या करेंगे?
                Remain calm and professional. Explain the applicable next steps according to company policy without threatening or pressuring the customer.
        
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
                - If customer say why you disturb then say "sorry, I dont want to disturb you i just reminding you about your loan." in hindi.
                **IMPORTANT :- Give only details that customer ask dont give another detail.
                    example :- if user ask due amount then give details of only due amount.
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
                model="saaras:v4",
                language_code="hi-IN"
            )
        
        stt_latency = time.perf_counter() - stt_start

        customer_message = stt_response.transcript.strip()
        if not customer_message:
            return None

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

        audio_base64 = tts_response.audios[0]

        # 5. Return data to the webpage
        return {
            "transcript": customer_message,
            "answer": answer,
            "audio_base64": audio_base64,
            "audio_mime_type": "audio/wav",
            "latency": {
                "stt": stt_latency,
                "llm": llm_latency,
                "tts": tts_latency
            }
        }

    finally:
        # 6. Delete the temporary audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
