import os
import base64
import sounddevice as sd
import soundfile as sf
from scipy.io.wavfile import write
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

customer = {
    "name": "Amit",
    "outstanding_amount": 5000,
    "due_date": "2026-10-10",
    "payment_status": "pending"
}

messages = [
    {
        "role": "system",
        "content": f"""
                        You are a polite female payment collection assistant from ABC Finance for payment related question.

                        Customer name: {customer["name"]}
                        Outstanding amount: Rs. {customer["outstanding_amount"]}
                        Due date: {customer["due_date"]}
                        Payment status: {customer["payment_status"]}

                        Be polite, concise, and respond in Hindi.
                        every day after due date has a penalty charge of 500 rupees.
                        Use only the provided customer information.
                        Never claim payment is completed without confirmation.
                        Do not invent payment details.
                    """
    }
]

SAMPLE_RATE = 16000
RECORD_SECONDS = 10

print("Payment Collection Voice Agent Started!")
print("Press Enter to speak. Type q and press Enter to quit.")

while True:
    command = input("\nReady ?")
    if command.strip().lower() == 'q' :
        print("\n Chat ended")
        break

    print("Recording start...., Speak Now!")
    # step1 :- Recording from microphone
    recording = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16"
    )
    sd.wait()

    write("mic_input.wav",SAMPLE_RATE,recording)
    print("\nRecording Completed ")

    # step2 :- sst works
    with open("mic_input.wav","rb") as audio_file:
        stt_response = client.speech_to_text.transcribe(
            file=audio_file,
            mode="transcribe",
            model="saaras:v4"
        )
    customer_message = stt_response.transcript.strip()

    # step3 :- LLM response
    messages.append(
        {
            "role" : "user",
            "content" : customer_message
        }
    )

    llm_response = client.chat.completions(
        model="sarvam-105b-conversations",
        max_tokens=1000,
        messages=messages
    )
    answer = llm_response.choices[0].message.content

    messages.append({
        "role" : "assistant",
        "content" : answer
    })

    # step4 :- tts response generation
    tts_response = client.text_to_speech.convert(
        model="bulbul:v3",
        text=answer,
        language_code="hi-IN",
        speaker="ritu"
    )
    audio_bytes = base64.b64decode(tts_response.audios[0])

    with open("response.wav","wb") as audio_file:
        audio_file.write(audio_bytes)

    # step5:- play agent reply

    audio_data,sample_rate = sf.read(
        "response.wav",
        dtype="float32"
    )

    print("\nplaying agent response...")
    sd.play(audio_data,sample_rate)
    sd.wait()

    print("\ncompleted")







