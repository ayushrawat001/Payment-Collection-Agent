import json
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException,Form
from fastapi.staticfiles import StaticFiles
from voice_agent import generate_opening_audio

from voice_agent import process_audio

app = FastAPI()
CUSTOMER_FILE = Path(__file__).parent/"temp_customers.json"

stt_latencies = []
llm_latencies = []
tts_latencies = []

@app.get("/api/customers/{cust_id}/opening")
def get_opening_message(cust_id: str):
    with open(CUSTOMER_FILE, "r", encoding="utf-8") as file:
        customers = json.load(file)

    customers = customers["customers"]

    customer = next(
        (c for c in customers if c["id"] == cust_id),
        None
    )

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return generate_opening_audio(customer)

@app.get("/api/customers/{cust_id}")
def get_customer(cust_id:str):
    with open(CUSTOMER_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    for customer in data["customers"]:
        if customer["id"] == cust_id:
            return customer

    raise HTTPException(
        status_code=404,
        detail="Customer Not Found"
    )

@app.post("/api/voice")
async def voice_endpoint(
    audio: UploadFile = File(...),
    cust_id: str = Form(...)
    ):
    try:
        audio_bytes = await audio.read()

        with open(CUSTOMER_FILE,"r",encoding="utf-8") as file:
            data = json.load(file)

        customer = None
        for item in data["customers"]:
            if item["id"] == cust_id:
                customer = item
                break

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer Not Found"
            )
        
        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="No audio received."
            )

        result = process_audio(
            audio_bytes,
            audio_extension=".webm",
            customer= customer,   
        )
        stt_latencies.append(result["latency"]["stt"])
        llm_latencies.append(result["latency"]["llm"])
        tts_latencies.append(result["latency"]["tts"])

        return result

    except HTTPException:
        raise

    except Exception as error:
        print("Voice agent error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Voice processing failed."
        )

@app.get("/api/kpi")
def get_kpi():
    return {
        "stt_avg": (
            sum(stt_latencies) / len(stt_latencies)
            if stt_latencies else None
        ),
        "llm_avg": (
            sum(llm_latencies) / len(llm_latencies)
            if llm_latencies else None
        ),
        "tts_avg": (
            sum(tts_latencies) / len(tts_latencies)
            if tts_latencies else None
        ),
        "total_responses": len(stt_latencies)
    }

app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)
