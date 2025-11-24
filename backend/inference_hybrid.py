#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid inference pipeline:
- Normalizes and enriches questions before RAG
- Validates retrieved chunks
- Builds concise, deterministic context summary
- Optionally calls Qwen-like model with strict prompt
- Cleans/validates final answer and falls back to deterministic response
"""

from __future__ import annotations

import os
import json
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from backend.inference import (
    normalize_input_text,
    needs_vietnamese_fallback,
)
from rag_pipeline_with_points import TrafficLawRAGWithPoints

DEFAULT_HF_TOKEN = "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"
DEFAULT_HF_REPO = "sigmaloop/qwen3-0.6B-instruct-trafficlaws"
DEFAULT_HF_SUBFOLDER = "model"


def strip_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics for fallback search queries."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


SYNONYM_MAP = {
    "vượt đèn đỏ": ["vượt tín hiệu", "không dừng đèn đỏ"],
    "không đội mũ": ["không đội nón", "không đội helmet"],
    "nồng độ cồn": ["uống rượu lái xe", "cồn vượt mức"],
    "lấn làn": ["đi sai làn", "đi nhầm làn"],
    "đi ngược chiều": ["chạy ngược chiều", "lưu thông ngược chiều"],
}


def expand_queries(question: str) -> List[str]:
    """Generate variations of the question to improve RAG recall."""
    base = normalize_input_text(question)
    variations = [base]

    stripped = strip_diacritics(base)
    if stripped.lower() != base.lower():
        variations.append(stripped)

    for key, synonyms in SYNONYM_MAP.items():
        if key in base.lower():
            variations.extend(synonyms)

    # Remove duplicates while keeping order
    seen = set()
    result = []
    for item in variations:
        if not item:
            continue
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


class HybridTrafficLawAssistant:
    """High-reliability assistant that chains RAG + Qwen with safeguards."""

    def __init__(
        self,
        data_path: Optional[str] = None,
        model_name: Optional[str] = None,
        use_generation: bool = True,
    ):
        self.data_path = data_path or os.getenv(
            "RAG_DATA_PATH",
            os.path.join(os.path.dirname(__file__), "..", "nd168_metadata_clean.json"),
        )
        raw_model_path = model_name or os.getenv("MODEL_PATH")
        self.model_repo = os.getenv("MODEL_HF_REPO", DEFAULT_HF_REPO)
        self.model_subfolder = os.getenv("MODEL_HF_SUBFOLDER", DEFAULT_HF_SUBFOLDER)

        local_model_default = (
            Path(__file__).resolve().parent.parent
            / "models"
            / "qwen3-0.6B-instruct-trafficlaws"
            / "model"
        )

        if raw_model_path:
            self.model_name = raw_model_path
            self.model_from_hub = False
        elif local_model_default.exists():
            self.model_name = str(local_model_default)
            self.model_from_hub = False
        else:
            self.model_name = self.model_repo
            self.model_from_hub = True

        self.use_generation = use_generation
        self.force_model_output = (
            os.getenv("FORCE_MODEL_OUTPUT", "false").lower() == "true"
        )
        self.hf_token = os.getenv("HF_TOKEN", DEFAULT_HF_TOKEN)

        self.rag = TrafficLawRAGWithPoints(self.data_path)
        self.tokenizer = None
        self.model = None
        if use_generation:
            self._load_model()

    def _load_model(self):
        """Load tokenizer/model with fallback."""
        tokenizer_kwargs = {"trust_remote_code": True}
        model_kwargs = {
            "trust_remote_code": True,
            "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
            "device_map": "auto" if torch.cuda.is_available() else None,
        }

        if self.model_from_hub:
            tokenizer_kwargs["token"] = self.hf_token
            model_kwargs["token"] = self.hf_token
            if self.model_subfolder:
                tokenizer_kwargs["subfolder"] = self.model_subfolder
                model_kwargs["subfolder"] = self.model_subfolder

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                **tokenizer_kwargs,
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **model_kwargs,
            )
            self.model.eval()
        except Exception as exc:
            print(f"[Hybrid] Primary model load failed: {exc}")
            backup = "Qwen/Qwen2.5-0.5B-Instruct"
            self.tokenizer = AutoTokenizer.from_pretrained(
                backup,
                trust_remote_code=True,
                token=self.hf_token,
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                backup,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
                token=self.hf_token,
            )
            self.model.eval()

    # --------------------------------------------------------------------- RAG
    def _retrieve_with_variations(self, question: str) -> Dict:
        """Try multiple query variations until RAG succeeds."""
        variations = expand_queries(question)
        last_result = None
        for variant in variations:
            result = self.rag.retrieve(variant)
            if result.get("status") == "success":
                if variant != question:
                    print(f"[Hybrid] RAG succeeded with variation: {variant}")
                return result
            last_result = result
        return last_result or {"status": "failed", "message": "Không tìm thấy thông tin"}

    def _validate_chunk(self, chunk: Dict) -> Dict:
        """Ensure chunk has required keys and trimmed content."""
        if not chunk:
            return {}
        sanitized = dict(chunk)
        content = sanitized.get("content", "")
        if content and len(content) > 300:
            sanitized["content"] = content[:300].strip() + "..."
        penalty = sanitized.get("penalty")
        if isinstance(penalty, dict) and penalty.get("text"):
            text = penalty["text"]
            if len(text) > 150:
                penalty["text"] = text[:150].strip() + "..."
        return sanitized

    def _format_context(self, retrieval_result: Dict) -> str:
        if retrieval_result.get("status") != "success":
            return ""
        primary = self._validate_chunk(retrieval_result.get("primary_chunk", {}))
        if not primary:
            return ""

        parts = ["=== THÔNG TIN LUẬT CHÍNH ==="]
        if primary.get("reference"):
            parts.append(f"Điều khoản: {primary['reference']}")
        if primary.get("content"):
            parts.append(f"Nội dung: {primary['content']}")
        penalty = primary.get("penalty", {}) or {}
        if penalty.get("text"):
            parts.append(f"Mức phạt: {penalty['text']}")
        if primary.get("point_deduction"):
            parts.append(f"Trừ điểm: {primary['point_deduction']} điểm")
        suspension = primary.get("license_suspension", {}) or {}
        if suspension.get("text"):
            parts.append(f"Tước GPLX: {suspension['text']}")

        related = retrieval_result.get("related_chunks") or []
        extra_lines = []
        for rel in related[:2]:
            rel = self._validate_chunk(rel)
            if rel.get("reference") and rel.get("penalty", {}).get("text"):
                extra_lines.append(f"- {rel['reference']}: {rel['penalty']['text']}")
        if extra_lines:
            parts.append("Thông tin bổ sung:")
            parts.extend(extra_lines)

        return "\n".join(parts)

    def _build_fallback_answer(self, retrieval_result: Dict) -> str:
        """Create a deterministic Vietnamese answer from retrieval data."""
        if retrieval_result.get("status") != "success":
            return "Xin lỗi, hiện chưa có thông tin cụ thể trong cơ sở dữ liệu."

        primary = retrieval_result.get("primary_chunk") or {}
        segments = []

        ref = primary.get("reference")
        if ref:
            segments.append(f"Theo {ref},")

        content = primary.get("content")
        if content:
            segments.append(content.strip())

        penalty = primary.get("penalty", {}) or {}
        if penalty.get("text"):
            segments.append(f"Mức phạt: {penalty['text']}.")

        point = primary.get("point_deduction")
        if point:
            segments.append(f"Trừ điểm: {point} điểm.")

        suspension = primary.get("license_suspension", {}) or {}
        if suspension.get("text"):
            segments.append(f"Tước GPLX: {suspension['text']}.")

        related = retrieval_result.get("related_chunks") or []
        extras = []
        for rel in related[:2]:
            rel_ref = rel.get("reference")
            rel_pen = (rel.get("penalty") or {}).get("text")
            if rel_ref and rel_pen:
                extras.append(f"{rel_ref}: {rel_pen}")

        if extras:
            segments.append("Thông tin bổ sung: " + "; ".join(extras) + ".")

        if not segments:
            return "Xin lỗi, hiện chưa có thông tin rõ ràng cho tình huống này."

        answer = " ".join(segments)
        # Basic cleanup: collapse whitespace, ensure Vietnamese punctuation spacing
        answer = " ".join(answer.split())
        return answer

    # -------------------------------------------------------------- Generation
    def _build_prompt(self, question: str, context: str, primary_reference: str) -> str:
        system_message = """Bạn là trợ lý pháp luật giao thông Việt Nam. Trả lời CHÍNH XÁC theo dữ liệu cung cấp.
Quy tắc:
- Luôn nêu đủ mức phạt tiền + trừ điểm + tước GPLX (nếu có).
- Sao chép đúng số tiền, số tháng, số điểm.
- Không thêm thông tin ngoài dữ liệu.
- Trả lời 2-3 câu, tiếng Việt chuẩn."""

        prompt = f"""<|im_start|>system
{system_message}<|im_end|>
<|im_start|>user
Câu hỏi: {question}

{context if context else '[Không có dữ liệu cụ thể trong cơ sở dữ liệu]'}
<|im_end|>
<|im_start|>assistant
Theo {primary_reference or 'quy định liên quan'}:"""
        return prompt

    def _clean_answer(self, answer: str) -> str:
        if not answer:
            return ""
        # Remove English/common filler similar to inference.py
        import re

        answer = re.sub(r'\d{4}-\d{2}-\d{2}.*', '', answer)
        chinese_patterns = [
            r'如果[^。]*。',
            r'法规',
            r'请[^。]*。',
            r'[^\x00-\x7F\u00C0-\u1EF9\s.,!?;:()\[\]{}\-]+',
        ]
        for pattern in chinese_patterns:
            answer = re.sub(pattern, '', answer)

        english_words = [
            'speed', 'red', 'color code', 'color', 'code', 'if there', 'if you',
            'please', 'thank you', 'months', 'month', 'if', 'there', 'you', 'can',
            'will', 'should', 'and', 'or', 'the', 'a', 'an', 'is', 'are', 'was',
            'were', 'be', 'been', 'being'
        ]
        for word in english_words:
            answer = re.sub(r'\b' + word + r'\b', '', answer, flags=re.IGNORECASE)

        answer = re.sub(r'\s+', ' ', answer).strip()
        return answer

    def _generate_with_model(self, question: str, retrieval_result: Dict, context: str):
        """Return (clean_answer, raw_answer) from the generative model."""
        if not self.model or not self.tokenizer:
            return "", ""

        primary = retrieval_result.get("primary_chunk", {}) or {}
        prompt = self._build_prompt(question, context, primary.get("reference"))
        inputs = self.tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        )
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=120,
                temperature=0.05,
                top_p=0.3,
                do_sample=True,
                repetition_penalty=1.2,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        raw_text = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
        if "<|im_start|>assistant" in raw_text:
            answer = raw_text.split("<|im_start|>assistant")[-1]
            if "<|im_end|>" in answer:
                answer = answer.split("<|im_end|>")[0]
        else:
            answer = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        cleaned = self._clean_answer(answer)
        if self.force_model_output:
            return cleaned or answer.strip(), answer.strip()

        if len(cleaned) < 20 or needs_vietnamese_fallback(cleaned):
            return "", answer.strip()
        return cleaned, answer.strip()

    def generate_from_prompt(
        self, prompt: str, max_new_tokens: int = 120
    ) -> tuple[str, str]:
        """Expose raw prompt generation for remote generator microservice."""
        if not self.use_generation:
            return "", ""
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model is not loaded")
        if not prompt:
            return "", ""

        inputs = self.tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        )
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        tokens = max(1, int(max_new_tokens or 1))
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=tokens,
                temperature=0.05,
                top_p=0.3,
                do_sample=True,
                repetition_penalty=1.2,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        raw_text = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
        if "<|im_start|>assistant" in raw_text:
            answer = raw_text.split("<|im_start|>assistant")[-1]
            if "<|im_end|>" in answer:
                answer = answer.split("<|im_end|>")[0]
        else:
            answer = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        cleaned = self._clean_answer(answer)
        if len(cleaned) < 20 or needs_vietnamese_fallback(cleaned):
            return "", answer.strip()
        return cleaned, answer.strip()

    # -------------------------------------------------------------- Public API
    def answer(self, question: str) -> Dict:
        normalized_question = normalize_input_text(question)
        retrieval_result = self._retrieve_with_variations(normalized_question)

        if retrieval_result.get("status") != "success":
            return {
                "status": "failed",
                "message": retrieval_result.get("message", "Không tìm thấy thông tin"),
            }

        context = self._format_context(retrieval_result)

        final_answer = ""
        raw_model_answer = ""
        used_generation = False
        if self.use_generation:
            final_answer, raw_model_answer = self._generate_with_model(
                normalized_question, retrieval_result, context
            )
            used_generation = bool(final_answer)

        if not final_answer:
            if self.force_model_output:
                final_answer = raw_model_answer or self._build_fallback_answer(
                    retrieval_result
                )
                source = "model_forced" if raw_model_answer else "fallback"
            else:
                final_answer = self._build_fallback_answer(retrieval_result)
                source = "fallback"
        else:
            source = "model"

        return {
            "status": "success",
            "question": normalized_question,
            "answer": final_answer,
            "context": context,
            "reference": retrieval_result.get("primary_chunk", {}).get("reference"),
            "source": source,
            "model_raw_answer": raw_model_answer,
        }


def quick_cli():
    assistant = HybridTrafficLawAssistant()
    while True:
        try:
            question = input("\nHỏi: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        result = assistant.answer(question)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    quick_cli()

