#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test RAG Pipeline with Point Deduction + Qwen 3 Model Integration
Uses rag_pipeline_with_points.py for enhanced point deduction tracking
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from rag_pipeline_with_points import TrafficLawRAGWithPoints
import json


class TrafficLawQAWithPoints:
    """Complete QA system with enhanced RAG + Qwen 3"""
    
    def __init__(self, data_path: str, model_name: str = r"D:\crawl_law\qwen3-0.6B-instruct-trafficlaws\checkpoint-13176"):
        print("Initializing Traffic Law QA System with Point Deduction...")
        
        # Initialize enhanced RAG
        print("\nLoading enhanced RAG pipeline...")
        self.rag = TrafficLawRAGWithPoints(data_path)
        
        # Load model and tokenizer
        print(f"\nLoading model: {model_name}")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True
            )
            
            if torch.cuda.is_available():
                print(f"   Model loaded on GPU: {torch.cuda.get_device_name(0)}")
            else:
                print(f"   Model loaded on CPU")
                
        except Exception as e:
            print(f"   Error loading model: {e}")
            print(f"   Trying backup model...")
            model_name = "Qwen/Qwen2.5-0.5B-Instruct"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True
            )
            print(f"   Loaded backup model: {model_name}")
        
        self.model.eval()
        print("\nSystem ready!")
    
    def format_context(self, retrieval_result: dict) -> str:
        """Format retrieval results into context for the model"""
        
        if retrieval_result["status"] != "success":
            return "Không tìm thấy thông tin liên quan."
        
        primary = retrieval_result["primary_chunk"]
        
        # Build context - FOCUS ON PRIMARY ONLY
        context_parts = [
            "=== ĐIỀU KHOẢN CHÍNH ===",
            f"Điều khoản: {primary['reference']}",
            f"\nNội dung quy định:",
            primary['content']
        ]
        
        # Add penalty info if available
        if primary.get('penalty'):
            penalty_text = primary['penalty']['text']
            context_parts.append(f"\nMức phạt tiền: {penalty_text}")
        else:
            context_parts.append(f"\nMức phạt: Tịch thu phương tiện")
        
        # Add point deduction if available
        if primary.get('point_deduction'):
            context_parts.append(f"Trừ điểm GPLX: {primary['point_deduction']} điểm")
        
        # Add license suspension if available
        if primary.get('license_suspension'):
            context_parts.append(f"Tước GPLX: {primary['license_suspension']['text']}")
        
        return "\n".join(context_parts)
    
    def generate_answer(self, query: str, retrieval_result: dict, max_length: int = 512) -> str:
        """Generate answer using Qwen 3 model"""
        
        # Format context
        context = self.format_context(retrieval_result)
        primary = retrieval_result["primary_chunk"]
        
        # Create prompt emphasizing the primary violation
        system_message = """Bạn là trợ lý tư vấn pháp luật giao thông Việt Nam.
Hãy trả lời câu hỏi dựa CHÍNH XÁC trên thông tin được cung cấp.

QUY TẮC BẮT BUỘC:
- PHẢI sao chép CHÍNH XÁC số tiền, số điểm, số tháng từ thông tin được cung cấp  
- PHẢI nêu ĐẦY ĐỦ: mức phạt tiền + trừ điểm (nếu có) + tước bằng (nếu có)
- KHÔNG bỏ sót bất kỳ hình phạt nào
- KHÔNG tự ý thay đổi con số
- Trả lời ngắn gọn 2-3 câu"""
        
        # Build structured answer template based on available info
        answer_parts = []
        if primary.get('penalty'):
            answer_parts.append("mức phạt tiền")
        if primary.get('point_deduction'):
            answer_parts.append("số điểm bị trừ")
        if primary.get('license_suspension'):
            answer_parts.append("thời gian tước bằng")
        
        answer_instruction = f"Hãy nêu rõ: {', '.join(answer_parts)}."
        
        # Simple, direct prompt that forces copying
        prompt = f"""<|im_start|>system
{system_message}<|im_end|>
<|im_start|>user
Câu hỏi: {query}

{context}

{answer_instruction}<|im_end|>
<|im_start|>assistant
Theo {primary['reference']}:"""
        
        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        
        # Move inputs to same device as model
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate - STRICT PARAMETERS TO PREVENT HALLUCINATION
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=150,  # Reduced from 512 - shorter answers, less hallucination
                temperature=0.1,     # MUCH lower - almost deterministic
                top_p=0.9,           # Slightly higher to avoid repetition loops
                do_sample=True,
                repetition_penalty=1.05,  # Minimal penalty to preserve numbers
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        # Decode
        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
        
        # Extract only the assistant's response
        if "<|im_start|>assistant" in full_response:
            answer = full_response.split("<|im_start|>assistant")[-1]
            if "<|im_end|>" in answer:
                answer = answer.split("<|im_end|>")[0]
            answer = answer.strip()
        else:
            answer = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            if query in answer:
                answer = answer.split(query)[-1].strip()
        
        return answer
    
    def ask(self, query: str, verbose: bool = True) -> dict:
        """Complete QA pipeline: retrieve + generate"""
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"QUESTION: {query}")
            print(f"{'='*80}")
        
        # Step 1: Retrieve
        if verbose:
            print("\n[1/2] Retrieving relevant law provisions...")
        
        retrieval_result = self.rag.retrieve(query)
        
        if retrieval_result["status"] != "success":
            return {
                "query": query,
                "status": "failed",
                "message": retrieval_result.get("message", "Không tìm thấy thông tin"),
                "answer": None
            }
        
        if verbose:
            print(f"   Found: {retrieval_result['primary_chunk']['reference']}")
            if retrieval_result.get('escalations_applied', 0) > 0:
                print(f"   Escalations applied: {retrieval_result['escalations_applied']}")
            if retrieval_result['primary_chunk'].get('point_deduction'):
                print(f"   Point deduction: {retrieval_result['primary_chunk']['point_deduction']} điểm")

        # Step 2: Generate
        if verbose:
            print("\n[2/2] Generating answer...")
        
        answer = self.generate_answer(query, retrieval_result)
        
        if verbose:
            print(f"   Answer generated ({len(answer)} characters)")
        
        return {
            "query": query,
            "status": "success",
            "retrieval": retrieval_result,
            "answer": answer
        }
    
    def print_result(self, result: dict):
        """Pretty print the result"""
        
        print(f"\n{'='*80}")
        print("RESULT")
        print(f"{'='*80}")
        
        if result["status"] == "success":
            print(f"\nANSWER:\n{result['answer']}")
            
            print(f"\nSOURCE:")
            primary = result['retrieval']['primary_chunk']
            print(f"   Reference: {primary['reference']}")
            if primary.get('penalty'):
                print(f"   Penalty: {primary['penalty']['text']}")
            if primary.get('point_deduction'):
                print(f"   Point Deduction: {primary['point_deduction']} điểm")
            if primary.get('license_suspension'):
                print(f"   License Suspension: {primary['license_suspension']['text']}")
            print(f"   Tags: {', '.join(primary['tags'])}")
            print(f"   Escalation: {primary['is_escalation']} (Priority: {primary['priority']})")
        else:
            print(f"\n❌ {result['message']}")
        
        print(f"\n{'='*80}")


def test_with_model():
    """Test the complete system with various queries"""
    
    # Initialize system
    qa_system = TrafficLawQAWithPoints(
        data_path=r"D:\crawl_law\nd168_metadata_clean.json",
        model_name=r"D:\crawl_law\qwen3-0.6B-instruct-trafficlaws\checkpoint-13176"
    )
    
    # Test cases
    test_cases = [
        # {
        #     "query": "đi xe máy không mang giấy phép lái xe thì sao?",
        #     "description": "Speeding 25km/h - should show 6-8M penalty + 6 points + 2-4 months suspension"
        # },
        # {
        #     "query": "lái ô tô không bật đèn thì sao?",
        #     "description": "Right turn causing accident - escalation case"
        # },
        # {
        #     "query": "cổ vũ, tụ tập đua xe máy bị phạt sao?",
        #     "description": "Right turn causing accident - escalation case"
        # },
        {
            "query": "Xe ô tô vượt đèn đỏ và gây tai nạn bị phạt bao nhiêu và trừ mấy điểm?",
            "description": "Red light violation with point deduction"
        },
        {
            "query": "Không đội mũ bảo hiểm khi đi xe máy có bị phạt không?",
            "description": "Motorcycle helmet violation"
        },
        {
            "query": "Xe ô tô rẽ phải sai quy định gây tai nạn thì phạt như thế nào?",
            "description": "Motorcycle helmet violation"
        },
        # {
        #     "query": "đi xe ô tô lạng lách đánh võng gây tai nạn phạt ra sao?",
        #     "description": "Motorcycle helmet violation"
        # }
    ]
    
    print("\n" + "="*80)
    print("TESTING RAG WITH POINT DEDUCTION + QWEN 3")
    print("="*80)
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'#'*80}")
        print(f"TEST CASE {i}/{len(test_cases)}: {test_case['description']}")
        print(f"{'#'*80}")
        
        result = qa_system.ask(test_case["query"], verbose=True)
        qa_system.print_result(result)
        
        results.append(result)
    
    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"Successful: {success_count}/{len(results)}")
    print(f"Failed: {len(results) - success_count}/{len(results)}")
    
    # Save results
    output_file = r"D:\crawl_law\qa_test_results_with_points.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    test_with_model()
