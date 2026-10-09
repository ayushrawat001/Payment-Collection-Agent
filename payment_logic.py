import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

customer = {
    "name" : "Amit",
    "outstanding_amount": 5000,
    "due_date": "2026-10-10",
    "payment_status": "pending"
}

system_prompt = f""""
You are a polite payment collection assistant.

Customer name: {customer["name"]}
Outstanding amount: ₹{customer["outstanding_amount"]}
Due date: {customer["due_date"]}
Payment status: {customer["payment_status"]}

Rules:
Be polite and concise.
Answer using the customer information provided.
If the customer requests more time, respond politely.
Never claim that a payment is completed without confirmation.
Do not invent payment details.
"""
customer_prompt = input("Hello, Please Write your query")

response = client.chat.completions(
    model="sarvam-105b-conversations",
    max_tokens=200,
    messages=[
        {
            "role" : "system",
            "content" : system_prompt
        },
        {
            "role" : "assistant",
            "content" : customer_prompt
        }
    ]
)

result = response.choices[0].message.content
print(result)
