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
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import requests
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
try:
    from unsloth import FastLanguageModel
    UNSLOTH_AVAILABLE = True
except ImportError:
    UNSLOTH_AVAILABLE = False
    FastLanguageModel = None

DEFAULT_SMALL_TALK_REPLY = (
    "Mình là trợ lý pháp luật giao thông, luôn sẵn sàng giải đáp các câu hỏi về "
    "xử phạt, mức phạt, trừ điểm, tước GPLX… Bạn cứ đặt câu hỏi liên quan đến luật giao thông nhé!"
)
DEFAULT_OUT_OF_SCOPE_REPLY = (
    "Xin lỗi, mình chỉ hỗ trợ các câu hỏi về luật và xử phạt giao thông đường bộ. "
    "Nếu bạn có tình huống vi phạm cụ thể, cứ mô tả chi tiết để mình tra cứu giúp."
)
SMALL_TALK_PATTERNS = [
    "bạn là ai",
    "bạn tên gì",
    "bạn làm gì",
    "bạn có khỏe không",
    "bạn khỏe không",
    "xin chào",
    "chào bạn",
    "hello",
    "hi ",
    "hi,",
    "hi.",
    "đang làm gì",
    "gì vậy",
    "ai đó không",
    "ở đó không",
]
OUT_OF_SCOPE_PATTERNS = [
    "bạn yêu",
    "người yêu",
    "thời tiết",
    "bóng đá",
    "chứng khoán",
    "crypto",
    "tiền ảo",
    "công nghệ thông tin",
    "học tiếng anh",
    "bán hàng",
    "ẩm thực",
]

# Patterns for non-traffic legal domains (criminal law, civil law, etc.)
NON_TRAFFIC_LEGAL_PATTERNS = [
    "luật hình sự",
    "hình sự",
    "tội",
    "tù",
    "án",
    "hình phạt",
    "bị cáo",
    "vụ án",
    "tòa án",
    "kiện",
    "luật dân sự",
    "dân sự",
    "hợp đồng",
    "thừa kế",
    "ly hôn",
    "tranh chấp",
    "luật lao động",
    "lao động",
    "bảo hiểm xã hội",
    "luật doanh nghiệp",
    "doanh nghiệp",
    "thuế",
    "luật thuế",
    "hải quan",
    "xuất nhập khẩu",
]
LEGAL_KEYWORDS = [
    "xe",
    "giao thông",
    "phạt",
    "mức phạt",
    "gplx",
    "tước",
    "điều",
    "khoản",
    "nồng độ cồn",
    "tốc độ",
    "đèn",
    "lỗi",
    "mũ bảo hiểm",
    "dừng",
    "đỗ",
    # Thêm các từ khóa về giao thông
    "vạch",
    "làn",
    "đường",
    "cấm",
    "tải",
    "chở",
    "ngược chiều",
    "giao lộ",
    "hầm",
    "cầu",
    "còi",
    "hàng",
    "khổ",
    "nguy hiểm",
    "rẽ",
    "quay đầu",
    "chuyển làn",
    "vượt",
    "cán",
    "đi vào",
    "khu vực",
    "cao tốc",
    "một chiều",
    "ưu tiên",
    "cứu thương",
    "công vụ",
    "đạp điện",
    "máy điện",
    "tổ chức",
    "doanh nghiệp",
    "vận tải",
    "bằng lái",
    "giấy tờ",
    "đăng ký",
    "bảo hiểm",
    "xi-nhan",
    "xi nhan",
    "đèn pha",
    "dây an toàn",
    "rượu",
    "bia",
    "cồn",
    "tai nạn",
    "trẻ em",
    "buýt",
    "tải",
    "đông dân cư",
    "hẹp",
    "mở cửa",
    "rác",
    "cảnh sát",
    "hiệu lệnh",
]

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

        self.default_max_new_tokens = int(os.getenv("MAX_NEW_TOKENS", "120"))
        self.max_new_tokens_limit = int(os.getenv("MAX_NEW_TOKENS_LIMIT", "512"))
        if self.max_new_tokens_limit < 1:
            self.max_new_tokens_limit = 512
        if self.default_max_new_tokens < 1:
            self.default_max_new_tokens = 120

        # Optional external question rewriter
        raw_rewriter_url = os.getenv("QUESTION_REWRITER_URL", "").strip()
        self.question_rewriter_url = raw_rewriter_url
        self.question_rewriter_token = os.getenv("QUESTION_REWRITER_TOKEN", "").strip()
        self.question_rewriter_model = os.getenv("QUESTION_REWRITER_MODEL", "").strip()
        try:
            self.question_rewriter_timeout = float(
                os.getenv("QUESTION_REWRITER_TIMEOUT", "6")
            )
        except ValueError:
            self.question_rewriter_timeout = 6.0

        self._question_rewriter_api_key = ""
        self.question_rewriter_enabled = bool(self.question_rewriter_url)
        if self.question_rewriter_enabled:
            parsed = urlparse(self.question_rewriter_url)
            query = parse_qs(parsed.query)
            api_key_from_url = ""
            if "key" in query and query["key"]:
                api_key_from_url = query["key"][0]
                query.pop("key", None)
                parsed = parsed._replace(query=urlencode(query, doseq=True))
                self.question_rewriter_url = urlunparse(parsed)
            self._question_rewriter_api_key = (
                self.question_rewriter_token or api_key_from_url
            )
            print(
                "[Hybrid] Question rewriter enabled -> "
                f"{self.question_rewriter_url}"
            )

        self.rag = TrafficLawRAGWithPoints(self.data_path)
        self.tokenizer = None
        self.model = None
        if use_generation:
            self._load_model()

    def _normalize_max_tokens(self, requested: Optional[int]) -> int:
        """Clamp requested max tokens into safe range."""
        if requested is None:
            return self.default_max_new_tokens
        try:
            value = int(requested)
        except (TypeError, ValueError):
            return self.default_max_new_tokens
        value = max(1, value)
        return min(value, self.max_new_tokens_limit)

    def _load_model(self):
        """Load tokenizer/model with unsloth (if available) or fallback to transformers."""
        use_unsloth = UNSLOTH_AVAILABLE and os.getenv("USE_UNSLOTH", "true").lower() == "true"
        
        if use_unsloth:
            try:
                print("[Hybrid] Loading model with unsloth...")
                # Unsloth uses the same model_name format as transformers
                model_name = self.model_name
                
                dtype = torch.float16 if torch.cuda.is_available() else torch.float32
                max_seq_length = 2048
                
                # Prepare kwargs for unsloth
                unsloth_kwargs = {
                    "model_name": model_name,
                    "max_seq_length": max_seq_length,
                    "dtype": dtype,
                    "load_in_4bit": False,  # Set to True if you want 4-bit quantization
                    "trust_remote_code": True,
                }
                
                # Add token and subfolder if loading from hub
                if self.model_from_hub:
                    unsloth_kwargs["token"] = self.hf_token
                    if self.model_subfolder:
                        # For unsloth, subfolder might need to be in model_name or handled differently
                        # Try with subfolder in path first
                        if "/" not in model_name:
                            model_name = f"{self.model_repo}/{self.model_subfolder}"
                        unsloth_kwargs["model_name"] = model_name
                
                self.model, self.tokenizer = FastLanguageModel.from_pretrained(**unsloth_kwargs)
                self.model.eval()
                print("[Hybrid] Model loaded successfully with unsloth")
                return
            except Exception as exc:
                print(f"[Hybrid] Unsloth load failed: {exc}, falling back to transformers")
                import traceback
                traceback.print_exc()
        
        # Fallback to transformers
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
        result = self.rag.retrieve(question)
        if result.get("status") == "success":
            return result
        return result or {"status": "failed", "message": "Không tìm thấy thông tin"}

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
            penalty = rel.get("penalty") or {}
            if rel.get("reference") and penalty.get("text"):
                extra_lines.append(f"- {rel['reference']}: {penalty['text']}")
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

    def _build_rag_citation_only(self, retrieval_result: Dict) -> str:
        """Build citation with only reference and related chunks (no primary chunk details)."""
        if retrieval_result.get("status") != "success":
            return ""
        
        primary = retrieval_result.get("primary_chunk") or {}
        segments = []
        
        # Only include reference, not full details (model already answered)
        ref = primary.get("reference")
        if ref:
            segments.append(f"Trích dẫn: {ref}")
        
        # Include related chunks as additional info
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
            return ""
        
        return " ".join(segments)

    # -------------------------------------------------------- Question rewrite
    def _rewrite_question(self, question: str) -> Optional[str]:
        """Optionally call external API to reformulate the question."""
        if not self.question_rewriter_enabled or not question.strip():
            return None

        is_gemini = "generativelanguage.googleapis.com" in (
            self.question_rewriter_url or ""
        ).lower()

        if is_gemini:
            rewrite_prompt = (
                "Hãy viết lại câu hỏi giao thông sau cho đầy đủ, rõ ràng, có đủ chủ thể "
                "và tình huống để tra cứu luật. Đảm bảo vẫn là tiếng Việt, không thêm dữ liệu bịa đặt.\n\n"
                f"Câu hỏi gốc: {question}\n"
                "Câu hỏi đã viết lại:"
            )
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": rewrite_prompt}
                        ],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.4,
                    "topP": 0.8,
                    "maxOutputTokens": 128,
                },
            }
        else:
            payload = {"input": question}
            if self.question_rewriter_model:
                payload["model"] = self.question_rewriter_model

        headers = {"Content-Type": "application/json"}
        if is_gemini:
            api_key = self._question_rewriter_api_key
            if not api_key:
                parsed = urlparse(self.question_rewriter_url)
                query = parse_qs(parsed.query)
                if "key" in query and query["key"]:
                    api_key = query["key"][0]
            if not api_key:
                print(
                    "[Hybrid] Question rewrite skipped: missing API key for Gemini endpoint."
                )
                return None
            if api_key:
                headers["x-goog-api-key"] = api_key
        elif self.question_rewriter_token:
            headers["Authorization"] = f"Bearer {self.question_rewriter_token}"

        try:
            resp = requests.post(
                self.question_rewriter_url,
                json=payload,
                headers=headers,
                timeout=self.question_rewriter_timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            rewritten = None
            if isinstance(data, dict):
                rewritten = (
                    data.get("rewritten")
                    or data.get("output")
                    or data.get("generated_text")
                )
                if not rewritten and "choices" in data:
                    choices = data.get("choices") or []
                    if choices:
                        first_choice = choices[0]
                        if isinstance(first_choice, dict):
                            rewritten = (
                                first_choice.get("text")
                                or first_choice.get("message", {}).get("content")
                            )
                if not rewritten and "candidates" in data:
                    candidates = data.get("candidates") or []
                    if candidates:
                        first_candidate = candidates[0]
                        if isinstance(first_candidate, dict):
                            content = first_candidate.get("content") or {}
                            if isinstance(content, dict):
                                parts = content.get("parts") or []
                                texts: List[str] = []
                                for part in parts:
                                    if isinstance(part, dict) and part.get("text"):
                                        texts.append(part["text"])
                                if texts:
                                    rewritten = " ".join(texts).strip()
                            # Some Gemini responses nest text directly under candidate
                            if not rewritten and first_candidate.get("output"):
                                rewritten = first_candidate["output"]
            elif isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    rewritten = (
                        first.get("generated_text")
                        or first.get("text")
                    )

            if rewritten:
                normalized = normalize_input_text(rewritten)
                if normalized and normalized != question:
                    print("[Hybrid] Question rewritten for clarity.")
                    return normalized
        except requests.HTTPError as http_err:
            detail = ""
            if http_err.response is not None:
                try:
                    detail = http_err.response.text
                except Exception:
                    detail = ""
            status = getattr(http_err.response, "status_code", "unknown")
            print(
                f"[Hybrid] Question rewrite failed (status {status}): "
                f"{detail or http_err}"
            )
        except Exception as exc:
            print(f"[Hybrid] Question rewrite failed: {exc}")
        return None

    # -------------------------------------------------------------- Generation
    def _build_prompt(self, question: str, context: str, primary_reference: str) -> str:
        system_message = """Bạn là trợ lý pháp luật GIAO THÔNG Việt Nam. CHỈ trả lời câu hỏi về luật và xử phạt GIAO THÔNG ĐƯỜNG BỘ.
Quy tắc:
- CHỈ trả lời câu hỏi về giao thông. Nếu câu hỏi về luật hình sự, dân sự, lao động, thuế, hoặc lĩnh vực khác, hãy từ chối và hướng dẫn người dùng hỏi về giao thông.
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
            'information', 'details', 'in the meantime', 'more information',
            'more details', 'please', 'thank you', 'should', 'however',
            'in summary', 'conclusion', 'detail', 'available', 'data',
            'reference', 'note', 'comment', 'english', 'months', 'month',
            'speed', 'color', 'code', 'if there', 'if you', 'in addition',
            'however', 'should', 'could', 'would', 'therefore'
        ]
        for word in english_words:
            answer = re.sub(r'\b' + re.escape(word) + r'\b', '', answer, flags=re.IGNORECASE)

        # Remove sentences that still look foreign
        sentences = re.split(r'(?<=[.!?])\s+', answer)
        filtered: list[str] = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            # Skip if contains non-Latin symbols (e.g. Chinese)
            if re.search(r'[\u4E00-\u9FFF]', sentence):
                continue
            # If sentence has tokens with Latin characters but no Vietnamese accents,
            # treat as foreign (allow short tokens like "AI")
            tokens = sentence.split()
            foreign_tokens = [
                tok for tok in tokens
                if re.search(r'[A-Za-z]', tok)
                and not re.search(r'[\u00C0-\u1EF9]', tok)
                and len(tok) > 2
            ]
            if foreign_tokens:
                continue
            filtered.append(sentence)

        answer = " ".join(filtered)
        answer = re.sub(r'\s+', ' ', answer).strip()
        return answer

    def _generate_with_model(
        self,
        question: str,
        retrieval_result: Dict,
        context: str,
        max_new_tokens: Optional[int] = None,
    ):
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

        tokens = self._normalize_max_tokens(max_new_tokens)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=tokens,
                temperature=0.6,
                top_p=0.95,
                top_k=20,
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
        
        # Filter out small talk responses (check both cleaned and raw answer)
        cleaned_lower = cleaned.lower()
        answer_lower = answer.lower()
        if (DEFAULT_SMALL_TALK_REPLY[:50].lower() in cleaned_lower or 
            "mình là trợ lý" in cleaned_lower or 
            "luôn sẵn sàng" in cleaned_lower or
            DEFAULT_SMALL_TALK_REPLY[:50].lower() in answer_lower or 
            "mình là trợ lý" in answer_lower):
            return "", answer.strip()  # Return empty to trigger fallback
        
        if self.force_model_output:
            return cleaned or answer.strip(), answer.strip()

        if len(cleaned) < 20 or needs_vietnamese_fallback(cleaned):
            return "", answer.strip()
        return cleaned, answer.strip()

    def generate_from_prompt(
        self, prompt: str, max_new_tokens: Optional[int] = None
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

        tokens = self._normalize_max_tokens(max_new_tokens)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=tokens,
                temperature=0.7,
                top_p=0.8,
                top_k=20,
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

    # --------------------------------------------------------------- Guardrails
    def _guardrail_classify(self, question: str) -> Optional[str]:
        """Detect small talk or out-of-scope queries before RAG/model."""
        if not question:
            return None
        normalized = question.lower().strip()
        normalized_no_diacritic = strip_diacritics(normalized)

        for phrase in SMALL_TALK_PATTERNS:
            p = phrase.lower()
            # Tránh nhận nhầm "hi" bên trong các từ tiếng Việt khi đã bỏ dấu (vd "thì", "khi")
            # -> các pattern bắt đầu bằng "hi" chỉ kiểm tra trên chuỗi có dấu và phải là từ riêng biệt
            if p.startswith("hi"):
                # Use word boundary to avoid matching "hi" inside "khi", "thì", etc.
                import re
                if re.search(r'\b' + re.escape(p.strip()) + r'\b', normalized):
                    return "small_talk"
            else:
                if p in normalized or p in normalized_no_diacritic:
                    return "small_talk"

        for phrase in OUT_OF_SCOPE_PATTERNS:
            if phrase in normalized or phrase in normalized_no_diacritic:
                return "out_of_scope"

        # Check for non-traffic legal domains (criminal law, civil law, etc.)
        for phrase in NON_TRAFFIC_LEGAL_PATTERNS:
            if phrase in normalized or phrase in normalized_no_diacritic:
                return "out_of_scope"

        # Heuristic: very short question without legal keywords -> out of scope
        # Tăng ngưỡng từ 4 lên 5 từ và kiểm tra kỹ hơn
        words = normalized.split()
        if len(words) <= 5:
            contains_legal = any(
                kw in normalized or kw in normalized_no_diacritic for kw in LEGAL_KEYWORDS
            )
            # Nếu câu hỏi có từ khóa về phương tiện hoặc hành vi giao thông, không chặn
            traffic_indicators = [
                "xe", "máy", "ô tô", "đạp", "tải", "buýt", "mô tô",
                "đi", "chạy", "dừng", "đỗ", "rẽ", "quay", "vượt", "chở",
                "đường", "làn", "vạch", "đèn", "cấm", "phạt", "vi phạm"
            ]
            has_traffic_indicator = any(
                ind in normalized or ind in normalized_no_diacritic 
                for ind in traffic_indicators
            )
            if not contains_legal and not has_traffic_indicator:
                return "out_of_scope"

        return None

    def _guardrail_response(self, mode: str, original_question: str) -> Dict:
        if mode == "small_talk":
            return {
                "status": "success",
                "question": original_question,
                "answer": DEFAULT_SMALL_TALK_REPLY,
                "context": "",
                "reference": None,
                "source": "guardrail_small_talk",
                "model_raw_answer": "",
            }
        return {
            "status": "success",
            "question": original_question,
            "answer": DEFAULT_OUT_OF_SCOPE_REPLY,
            "context": "",
            "reference": None,
            "source": "guardrail_out_of_scope",
            "model_raw_answer": "",
        }

    def _answer_without_rag(self, question: str, max_new_tokens: Optional[int] = None) -> Dict:
        """Generate answer directly from model without RAG retrieval."""
        if not self.use_generation or not self.model or not self.tokenizer:
            return {
                "status": "failed",
                "message": "Model không khả dụng. Vui lòng bật RAG để sử dụng cơ sở dữ liệu.",
            }
        
        # Build prompt without RAG context
        system_message = """Bạn là trợ lý pháp luật GIAO THÔNG Việt Nam. CHỈ trả lời câu hỏi về luật và xử phạt GIAO THÔNG ĐƯỜNG BỘ.
Quy tắc:
- CHỈ trả lời câu hỏi về giao thông. Nếu câu hỏi về luật hình sự, dân sự, lao động, thuế, hoặc lĩnh vực khác, hãy từ chối và hướng dẫn người dùng hỏi về giao thông.
- Trả lời chính xác về mức phạt, trừ điểm, tước GPLX nếu bạn biết.
- Nếu không chắc chắn, hãy nói rõ bạn không có thông tin cụ thể.
- Trả lời 2-3 câu, tiếng Việt chuẩn."""
        
        prompt = f"""<|im_start|>system
{system_message}<|im_end|>
<|im_start|>user
Câu hỏi: {question}
<|im_end|>
<|im_start|>assistant
"""
        
        inputs = self.tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        )
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        tokens = self._normalize_max_tokens(max_new_tokens)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=tokens,
                temperature=0.7,
                top_p=0.8,
                top_k=20,
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
            cleaned = answer.strip()
        
        # Check if answer indicates out-of-scope (non-traffic legal domain)
        cleaned_lower = cleaned.lower()
        out_of_scope_indicators = [
            "hình sự",
            "dân sự",
            "lao động",
            "thuế",
            "không phải giao thông",
            "không liên quan đến giao thông",
            "chỉ hỗ trợ giao thông",
        ]
        if any(indicator in cleaned_lower for indicator in out_of_scope_indicators):
            # Model correctly rejected out-of-scope question
            return {
                "status": "success",
                "question": question,
                "answer": DEFAULT_OUT_OF_SCOPE_REPLY,
                "context": "",
                "reference": None,
                "source": "model_no_rag_rejected",
                "model_raw_answer": answer.strip(),
            }
        
        return {
            "status": "success",
            "question": question,
            "answer": cleaned,
            "context": "",
            "reference": None,
            "source": "model_no_rag",
            "model_raw_answer": answer.strip(),
        }

    # -------------------------------------------------------------- Public API
    def answer(self, question: str, max_new_tokens: Optional[int] = None, use_rag: bool = True) -> Dict:
        normalized_question = normalize_input_text(question)
        guardrail_mode = self._guardrail_classify(normalized_question)
        if guardrail_mode:
            return self._guardrail_response(guardrail_mode, question)

        rewritten = self._rewrite_question(normalized_question)
        if rewritten:
            normalized_question = rewritten

        # Skip RAG if disabled
        if not use_rag:
            # Direct model generation without RAG context
            return self._answer_without_rag(normalized_question, max_new_tokens)

        retrieval_result = self._retrieve_with_variations(normalized_question)

        retrieval_success = retrieval_result.get("status") == "success"
        context = self._format_context(retrieval_result) if retrieval_success else ""

        final_answer = ""
        raw_model_answer = ""
        used_generation = False
        if self.use_generation:
            generation_payload = (
                retrieval_result if retrieval_success else {"primary_chunk": {}}
            )
            final_answer, raw_model_answer = self._generate_with_model(
                normalized_question,
                generation_payload,
                context,
                max_new_tokens=max_new_tokens,
            )
            used_generation = bool(final_answer)
            
            # Filter out small talk responses even when RAG succeeds
            if final_answer:
                final_lower = final_answer.lower()
                small_talk_patterns = [
                    DEFAULT_SMALL_TALK_REPLY[:50].lower(),
                    "mình là trợ lý",
                    "luôn sẵn sàng",
                    "bạn cứ đặt câu hỏi",
                    "trợ lý pháp luật giao thông",
                    "sẵn sàng giải đáp"
                ]
                is_small_talk = any(pattern in final_lower for pattern in small_talk_patterns)
                if is_small_talk:
                    print(f"[FILTER] Detected small talk in model output, clearing answer")
                    print(f"[FILTER] Model output: {final_answer[:100]}...")
                    # Model returned small talk despite having RAG context, use fallback
                    final_answer = ""
                    used_generation = False

        if not final_answer:
            if self.force_model_output:
                final_answer = raw_model_answer or self._build_fallback_answer(
                    retrieval_result
                )
                if raw_model_answer:
                    source = "model_forced"
                elif retrieval_success:
                    source = "fallback"
                else:
                    source = "model_forced_no_rag"
            elif raw_model_answer and not retrieval_success:
                # Filter out small talk responses when RAG fails
                raw_lower = raw_model_answer.lower()
                if (DEFAULT_SMALL_TALK_REPLY[:50].lower() in raw_lower or 
                    "mình là trợ lý" in raw_lower or 
                    "luôn sẵn sàng" in raw_lower):
                    # Model returned small talk, use fallback message instead
                    final_answer = "Xin lỗi, hiện chưa có thông tin cụ thể trong cơ sở dữ liệu về câu hỏi này. Vui lòng thử lại với câu hỏi cụ thể hơn về vi phạm giao thông."
                    source = "fallback_no_rag"
                else:
                    # Check if model correctly rejected out-of-scope question
                    out_of_scope_indicators = [
                        "hình sự",
                        "dân sự",
                        "lao động",
                        "thuế",
                        "không phải giao thông",
                        "không liên quan đến giao thông",
                        "chỉ hỗ trợ giao thông",
                    ]
                    if any(indicator in raw_lower for indicator in out_of_scope_indicators):
                        # Model correctly rejected, use out-of-scope reply
                        final_answer = DEFAULT_OUT_OF_SCOPE_REPLY
                        source = "model_no_rag_rejected"
                    else:
                        final_answer = raw_model_answer.strip()
                        source = "model_no_rag"
            else:
                if retrieval_success:
                    final_answer = self._build_fallback_answer(retrieval_result)
                    source = "fallback"
                else:
                    return {
                        "status": "failed",
                        "message": retrieval_result.get(
                            "message", "Không tìm thấy thông tin"
                        ),
                    }
        else:
            source = "model" if retrieval_success else "model_no_rag"
            
            # Final check: filter out small talk even in final answer
            final_lower = final_answer.lower()
            # More comprehensive small talk detection
            small_talk_indicators = [
                DEFAULT_SMALL_TALK_REPLY[:50].lower(),
                "mình là trợ lý",
                "luôn sẵn sàng",
                "bạn cứ đặt câu hỏi",
                "trợ lý pháp luật giao thông",
                "trợ lý pháp luật",
                "sẵn sàng giải đáp",
                "câu hỏi liên quan đến luật giao thông",
                "đặt câu hỏi liên quan"
            ]
            # Check if answer starts with or contains small talk patterns
            is_small_talk = any(
                indicator in final_lower or final_lower.startswith(indicator[:20])
                for indicator in small_talk_indicators
            )
            
            if is_small_talk:
                print(f"[FILTER] Detected small talk in final answer, replacing with fallback")
                print(f"[FILTER] Original answer: {final_answer[:100]}...")
                # Replace with fallback if retrieval succeeded, otherwise use error message
                if retrieval_success:
                    final_answer = self._build_fallback_answer(retrieval_result)
                    source = "fallback"
                    print(f"[FILTER] Using fallback answer from RAG")
                else:
                    final_answer = "Xin lỗi, hiện chưa có thông tin cụ thể trong cơ sở dữ liệu về câu hỏi này. Vui lòng thử lại với câu hỏi cụ thể hơn về vi phạm giao thông."
                    source = "fallback_no_rag"
                    print(f"[FILTER] Using error message (no RAG)")
            else:
                # Not small talk: keep model answer but append RAG citation if available
                if retrieval_success:
                    primary = retrieval_result.get("primary_chunk", {}) or {}
                    primary_ref = primary.get("reference", "")
                    
                    # Check if model answer already contains the reference and penalty info
                    # If yes, don't append citation to avoid duplication
                    final_lower = final_answer.lower()
                    has_reference = primary_ref and primary_ref.lower() in final_lower
                    has_penalty = "mức phạt" in final_lower or "phạt" in final_lower
                    
                    # Only append citation if model answer doesn't already have complete info
                    if not (has_reference and has_penalty):
                        # Only append reference and related chunks, not full fallback (to avoid duplication)
                        rag_citation = self._build_rag_citation_only(retrieval_result)
                        if rag_citation:
                            print("[FILTER] Appending RAG citation to model answer")
                            final_answer = final_answer.strip()
                            final_answer += "\n\n---\n"
                            final_answer += rag_citation
                            source = "model_with_rag_citation"
                    else:
                        print("[FILTER] Model answer already contains complete info, skipping citation")
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

