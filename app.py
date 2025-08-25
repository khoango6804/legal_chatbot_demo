from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os

from inference import get_answer_stream

app = FastAPI()

# Allow CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/img", StaticFiles(directory="img"), name="img")

class ChatRequest(BaseModel):
    question: str
    chat_history: list = []  # List of [user_message, ai_response] pairs

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    def answer_stream():
        for chunk in get_answer_stream(req.question, req.chat_history):
            yield chunk
    return StreamingResponse(answer_stream(), media_type="text/plain")

@app.get("/speed")
async def get_speed_info():
    """Trả về thông tin về tốc độ xử lý của model"""
    return JSONResponse({
        "info": "Sử dụng endpoint /chat để xem tốc độ token/s thực tế",
        "note": "Tốc độ sẽ được hiển thị ở đầu câu trả lời"
    })

@app.get("/")
async def root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True) 