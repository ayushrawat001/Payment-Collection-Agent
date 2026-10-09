import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

response = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[
        {
            "role": "system",
            "content": """
            You are a polite payment collection assistant
            for ABC Finance.

            Customer name: Amit
            Outstanding amount: Rs. 5000
            Due date: 10 October 2026

            Be polite and concise.
            Use only the customer information provided.
            Never claim that a payment has been made
            unless the system confirms it.
            """
        },
        {
            "role": "user",
            "content": "I cannot pay today. Can I pay tomorrow?"
        },
    ],
    max_tokens=200
)
print(response.choices[0].message.content)