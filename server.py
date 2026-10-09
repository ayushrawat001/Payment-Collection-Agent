from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles

from voice_agent import process_audio

app = FastAPI()


@app.post("/api/voice")
async def voice_endpoint(audio: UploadFile = File(...)):
    try:
        audio_bytes = await audio.read()

        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="No audio received."
            )

        result = process_audio(
            audio_bytes,
            audio_extension=".webm"
        )

        return result

    except HTTPException:
        raise

    except Exception as error:
        print("Voice agent error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Voice processing failed."
        )


app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)
