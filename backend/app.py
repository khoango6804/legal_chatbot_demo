from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uvicorn
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.inference import normalize_input_text
from backend.database import init_db, get_db, Feedback
from fastapi.staticfiles import StaticFiles
from backend.inference_hybrid import HybridTrafficLawAssistant

app = FastAPI(title="Legal AI Assistant API", version="1.0.0")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR, html=False), name="static")
IMAGES_DIR = FRONTEND_DIR / "img"
if IMAGES_DIR.exists():
    app.mount("/img", StaticFiles(directory=IMAGES_DIR, html=False), name="images")

# Hybrid assistant globals
assistant: Optional[HybridTrafficLawAssistant] = None
USE_GENERATIVE_MODEL = os.getenv("USE_GENERATIVE_MODEL", "true").lower() == "true"


def get_hybrid_assistant() -> HybridTrafficLawAssistant:
    """Lazy-initialize the HybridTrafficLawAssistant once per process."""
    global assistant
    if assistant is None:
        assistant = HybridTrafficLawAssistant(use_generation=USE_GENERATIVE_MODEL)
    return assistant

# Khởi tạo database khi start app
@app.on_event("startup")
async def startup_event():
    init_db()

    print("=" * 60)
    print("Preloading HybridTrafficLawAssistant...")
    print("=" * 60)
    try:
        helper = get_hybrid_assistant()
        loaded = (not helper.use_generation) or (helper.model is not None)
        if loaded:
            print("[OK] Hybrid assistant ready!")
        else:
            print("[WARNING] Hybrid assistant initialized without generative model; deterministic answers only.")
    except Exception as e:
        print(f"[WARNING] Error initializing hybrid assistant: {e}")
        print("   Will retry on first user request.")

# CORS configuration - cho phép frontend gọi API
# Trong production, nên set allow_origins cụ thể thay vì "*"
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str
    chat_history: list = []  # List of [user_message, ai_response] pairs
    max_tokens: Optional[int] = None

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    feedback_type: str  # "wrong", "error", "improvement"
    message: str = ""  # Optional feedback message

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Endpoint để chat với AI model"""
    # Log and normalize question encoding before processing
    try:
        raw_question = req.question
        normalized_question = normalize_input_text(raw_question)
        print(f"[API] Question raw repr: {repr(raw_question)}")
        if normalized_question != raw_question:
            print(f"[API] Question normalized repr: {repr(normalized_question)}")
    except Exception as e:
        print(f"[API] Error normalizing question: {e}")
        normalized_question = req.question

    requested_max_tokens = req.max_tokens

    def answer_stream():
        helper = get_hybrid_assistant()
        try:
            result = helper.answer(
                normalized_question, max_new_tokens=requested_max_tokens
            )
        except Exception as exc:
            print(f"[API] Hybrid assistant error: {exc}")
            yield "Xin lỗi, hệ thống đang gặp sự cố khi tạo câu trả lời. "
            return

        if result.get("status") != "success":
            fallback_message = result.get("message") or "Xin lỗi, hiện chưa có thông tin phù hợp trong cơ sở dữ liệu."
            for word in fallback_message.split():
                yield word + " "
            return

        answer_text = result.get("answer") or ""
        if not answer_text.strip():
            answer_text = "Xin lỗi, hiện chưa có thông tin rõ ràng cho tình huống này."

        for word in answer_text.split():
            yield word + " "

    return StreamingResponse(answer_stream(), media_type="text/plain")

@app.get("/speed")
async def get_speed_info():
    """Trả về thông tin về tốc độ xử lý của model"""
    return JSONResponse({
        "info": "Sử dụng endpoint /chat để xem tốc độ token/s thực tế",
        "note": "Tốc độ sẽ được hiển thị ở đầu câu trả lời"
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    helper = assistant
    model_loaded = False
    if helper is not None:
        model_loaded = (not helper.use_generation) or (helper.model is not None)
    else:
        # Try lazy-init without forcing heavy load on health hits
        try:
            helper = get_hybrid_assistant()
            model_loaded = (not helper.use_generation) or (helper.model is not None)
        except Exception as exc:
            print(f"[API] Health check unable to init hybrid assistant: {exc}")
            model_loaded = False

    return JSONResponse({
        "status": "healthy", 
        "service": "Legal AI Assistant API",
        "model_loaded": model_loaded,
        "use_generation": helper.use_generation if helper else USE_GENERATIVE_MODEL
    })

@app.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Endpoint để nhận feedback từ người dùng"""
    try:
        # Validate feedback_type
        valid_types = ["wrong", "error", "improvement"]
        if feedback.feedback_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"feedback_type must be one of: {', '.join(valid_types)}"
            )
        
        # Lấy thông tin client
        user_agent = request.headers.get("user-agent", "")
        ip_address = request.client.host if request.client else None
        
        # Tạo feedback record
        db_feedback = Feedback(
            question=feedback.question,
            answer=feedback.answer,
            feedback_type=feedback.feedback_type,
            message=feedback.message,
            user_agent=user_agent[:500],  # Giới hạn độ dài
            ip_address=ip_address,
            created_at=datetime.utcnow()
        )
        
        db.add(db_feedback)
        db.commit()
        db.refresh(db_feedback)
        
        return JSONResponse({
            "success": True,
            "message": "Cảm ơn bạn đã gửi phản hồi! Chúng tôi sẽ xem xét và cải thiện.",
            "feedback_id": db_feedback.id
        })
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi lưu feedback")

@app.get("/feedback")
async def get_feedback(
    skip: int = 0,
    limit: int = 50,
    resolved: bool = None,
    db: Session = Depends(get_db)
):
    """Endpoint để xem feedback (admin only - có thể thêm authentication sau)"""
    try:
        query = db.query(Feedback)
        
        # Filter by resolved status if provided
        if resolved is not None:
            query = query.filter(Feedback.is_resolved == resolved)
        
        # Order by created_at desc
        query = query.order_by(Feedback.created_at.desc())
        
        # Pagination
        total = query.count()
        feedbacks = query.offset(skip).limit(limit).all()
        
        return JSONResponse({
            "total": total,
            "skip": skip,
            "limit": limit,
            "feedbacks": [f.to_dict() for f in feedbacks]
        })
    except Exception as e:
        print(f"Error getting feedback: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi lấy feedback")

@app.patch("/feedback/{feedback_id}/resolve")
async def resolve_feedback(
    feedback_id: int,
    db: Session = Depends(get_db)
):
    """Đánh dấu feedback đã được xử lý"""
    try:
        feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        feedback.is_resolved = True
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": "Feedback đã được đánh dấu là đã xử lý"
        })
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error resolving feedback: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi cập nhật feedback")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app:app", host=host, port=port, reload=False)

