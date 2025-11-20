#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remote generator microservice.

Run on a separate machine with sufficient resources to host the generative model.
Receives fully formatted prompts from the main backend and returns model outputs.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel
from backend.inference_hybrid import HybridTrafficLawAssistant


class GenerateRequest(BaseModel):
    prompt: str
    question: Optional[str] = ""
    max_new_tokens: int = 120


class GenerateResponse(BaseModel):
    answer: str
    raw_answer: str


app = FastAPI(title="Remote Generator Service", version="1.0.0")

# Lazy init to avoid loading model before first request if desired.
assistant: Optional[HybridTrafficLawAssistant] = None
REMOTE_GENERATOR_TOKEN = os.getenv("REMOTE_GENERATOR_TOKEN", "").strip() or None
AUTH_HEADER_PREFIX = "bearer "


def get_assistant() -> HybridTrafficLawAssistant:
    global assistant
    if assistant is None:
        assistant = HybridTrafficLawAssistant(use_generation=True)
    return assistant


def verify_authorization(authorization: Optional[str] = Header(default=None)) -> None:
    """Basic bearer token guard (optional)."""
    if not REMOTE_GENERATOR_TOKEN:
        return
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    auth = authorization.strip()
    if not auth.lower().startswith(AUTH_HEADER_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme",
        )
    provided = auth[len(AUTH_HEADER_PREFIX) :].strip()
    if not provided or provided != REMOTE_GENERATOR_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token"
        )


@app.post("/generate", response_model=GenerateResponse)
def generate(
    req: GenerateRequest, _: None = Depends(verify_authorization)
) -> GenerateResponse:
    try:
        helper = get_assistant()
        answer, raw = helper.generate_from_prompt(
            req.prompt, max_new_tokens=req.max_new_tokens
        )
        if not answer:
            answer = raw
        return GenerateResponse(answer=answer or "", raw_answer=raw or "")
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
def health_check(_: None = Depends(verify_authorization)):
    loaded = assistant is not None and assistant.model is not None
    return {
        "status": "healthy" if loaded else "initializing",
        "model_loaded": loaded,
    }

