#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alternative inference module that mirrors the behaviour in test_rag_duong_gui.py.

This file keeps the standalone QA pipeline (RAG + Qwen) exactly like the test
script, but packages it so it can be reused outside the test harness.
"""

import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Allow importing RAG pipeline when running inside backend package
CURRENT_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if ROOT_DIR not in os.sys.path:
    os.sys.path.insert(0, ROOT_DIR)

from rag_pipeline_with_points import TrafficLawRAGWithPoints  # noqa: E402


def get_default_paths():
    """Helper to compute default data/model paths."""
    data_path = os.getenv(
        "RAG_DATA_PATH",
        os.path.join(ROOT_DIR, "nd168_metadata_clean.json"),
    )

    model_path = os.getenv("MODEL_PATH")
    if not model_path:
        # Fall back to HF repo style if provided
        model_path = os.getenv("MODEL_HF_REPO")
    if not model_path:
        model_path = os.path.join(ROOT_DIR, "qwen3-0.6B-instruct-trafficlaws", "model")

    return data_path, model_path


class TrafficLawQAWithPoints:
    """Complete QA system with enhanced RAG + Qwen 3 (mirrors test script)."""

    def __init__(self, data_path: str = None, model_name: str = None):
        data_path = data_path or get_default_paths()[0]
        model_name = model_name or get_default_paths()[1]

        print("Initializing Traffic Law QA System with Point Deduction...")
        print("\nLoading enhanced RAG pipeline...")
        self.rag = TrafficLawRAGWithPoints(data_path)

        print(f"\nLoading model: {model_name}")
        self.tokenizer, self.model = self._load_model(model_name)
        self.model.eval()
        print("\nSystem ready!")

    def _load_model(self, model_name):
        """Load tokenizer/model with optional fallback."""
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
            )
            if torch.cuda.is_available():
                print(f"   Model loaded on GPU: {torch.cuda.get_device_name(0)}")
            else:
                print("   Model loaded on CPU")
            return tokenizer, model
        except Exception as exc:
            print(f"   Error loading model: {exc}")
            print("   Trying backup model Qwen/Qwen2.5-0.5B-Instruct ...")
            backup = "Qwen/Qwen2.5-0.5B-Instruct"
            tokenizer = AutoTokenizer.from_pretrained(backup, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                backup,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
            )
            return tokenizer, model

    def format_context(self, retrieval_result: dict) -> str:
        """Format retrieval results into context for the model."""
        if retrieval_result.get("status") != "success":
            return "Không tìm thấy thông tin liên quan."

        primary = retrieval_result["primary_chunk"]
        context_parts = [
            "=== ĐIỀU KHOẢN CHÍNH ===",
            f"Điều khoản: {primary['reference']}",
            "\nNội dung quy định:",
            primary["content"],
        ]

        penalty = primary.get("penalty")
        if penalty:
            context_parts.append(f"\nMức phạt tiền: {penalty['text']}")
        else:
            context_parts.append("\nMức phạt: Tịch thu phương tiện")

        if primary.get("point_deduction"):
            context_parts.append(f"Trừ điểm GPLX: {primary['point_deduction']} điểm")
        if primary.get("license_suspension"):
            context_parts.append(f"Tước GPLX: {primary['license_suspension']['text']}")

        return "\n".join(context_parts)

    def _build_prompt(self, query: str, retrieval_result: dict):
        """Build the strict prompt identical to the test script."""
        context = self.format_context(retrieval_result)
        primary = retrieval_result["primary_chunk"]

        system_message = """Bạn là trợ lý tư vấn pháp luật giao thông Việt Nam.
Hãy trả lời câu hỏi dựa CHÍNH XÁC trên thông tin được cung cấp.

QUY TẮC BẮT BUỘC:
- PHẢI sao chép CHÍNH XÁC số tiền, số điểm, số tháng từ thông tin được cung cấp
- PHẢI nêu ĐẦY ĐỦ: mức phạt tiền + trừ điểm (nếu có) + tước bằng (nếu có)
- KHÔNG bỏ sót bất kỳ hình phạt nào
- KHÔNG tự ý thay đổi con số
- Trả lời ngắn gọn 2-3 câu"""

        answer_requirements = []
        if primary.get("penalty"):
            answer_requirements.append("mức phạt tiền")
        if primary.get("point_deduction"):
            answer_requirements.append("số điểm bị trừ")
        if primary.get("license_suspension"):
            answer_requirements.append("thời gian tước bằng")

        answer_instruction = (
            f"Hãy nêu rõ: {', '.join(answer_requirements)}."
            if answer_requirements
            else "Hãy nêu rõ mức phạt theo thông tin trên."
        )

        prompt = f"""<|im_start|>system
{system_message}<|im_end|>
<|im_start|>user
Câu hỏi: {query}

{context}

{answer_instruction}<|im_end|>
<|im_start|>assistant
Theo {primary['reference']}:"""
        return prompt

    def generate_answer(self, query: str, retrieval_result: dict) -> str:
        """Generate answer using the strict prompt."""
        prompt = self._build_prompt(query, retrieval_result)
        inputs = self.tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        )

        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=150,
                temperature=0.1,
                top_p=0.9,
                do_sample=True,
                repetition_penalty=1.05,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
        if "<|im_start|>assistant" in full_response:
            answer = full_response.split("<|im_start|>assistant")[-1]
            if "<|im_end|>" in answer:
                answer = answer.split("<|im_end|>")[0]
            return answer.strip()

        answer = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        if query in answer:
            answer = answer.split(query)[-1].strip()
        return answer

    def ask(self, query: str, verbose: bool = False) -> dict:
        """Complete QA pipeline: retrieve + generate."""
        if verbose:
            print("\n" + "=" * 80)
            print(f"QUESTION: {query}")
            print("=" * 80)

        if verbose:
            print("\n[1/2] Retrieving relevant law provisions...")
        retrieval_result = self.rag.retrieve(query)

        if retrieval_result.get("status") != "success":
            return {
                "query": query,
                "status": "failed",
                "message": retrieval_result.get("message", "Không tìm thấy thông tin"),
                "answer": None,
            }

        if verbose:
            primary = retrieval_result["primary_chunk"]
            print(f"   Found: {primary['reference']}")
            if primary.get("point_deduction"):
                print(f"   Point deduction: {primary['point_deduction']} điểm")

        if verbose:
            print("\n[2/2] Generating answer...")
        answer = self.generate_answer(query, retrieval_result)
        if verbose:
            print(f"   Answer generated ({len(answer)} characters)")

        return {
            "query": query,
            "status": "success",
            "retrieval": retrieval_result,
            "answer": answer,
        }

    def print_result(self, result: dict):
        """Pretty print helper identical to test script."""
        print("\n" + "=" * 80)
        print("RESULT")
        print("=" * 80)
        if result["status"] != "success":
            print(f"\nERROR: {result['message']}")
            return

        print(f"\nANSWER:\n{result['answer']}")
        primary = result["retrieval"]["primary_chunk"]
        print("\nSOURCE:")
        print(f"   Reference: {primary['reference']}")
        if primary.get("penalty"):
            print(f"   Penalty: {primary['penalty']['text']}")
        if primary.get("point_deduction"):
            print(f"   Point Deduction: {primary['point_deduction']} điểm")
        if primary.get("license_suspension"):
            print(f"   License Suspension: {primary['license_suspension']['text']}")
        print(f"   Tags: {', '.join(primary.get('tags', []))}")


def run_quick_test():
    """Simple CLI runner to mimic test_rag_duong_gui behaviour."""
    qa = TrafficLawQAWithPoints()
    sample_questions = [
        "Xe ô tô vượt đèn đỏ và gây tai nạn bị phạt bao nhiêu và trừ mấy điểm?",
        "Không đội mũ bảo hiểm khi đi xe máy có bị phạt không?",
    ]
    results = []
    for question in sample_questions:
        result = qa.ask(question, verbose=True)
        qa.print_result(result)
        results.append(result)

    summary = {
        "success": sum(1 for r in results if r["status"] == "success"),
        "total": len(results),
    }
    print("\nSUMMARY:", summary)
    return results


if __name__ == "__main__":
    run_quick_test()

