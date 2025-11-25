"""
Test RAG pipeline for ND168 + Luật TTATGTĐB with LLM generation
Using Qwen3-0.6B-instruct checkpoint
"""

from rag_nd168_ttatgtdb import TrafficLawRAG2Laws
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

class RAGWithLLM:
    """RAG pipeline with LLM for answer generation"""
    
    def __init__(self, rag_pipeline, model_path: str):
        """
        Initialize RAG + LLM
        
        Args:
            rag_pipeline: Initialized RAG pipeline
            model_path: Path to fine-tuned model checkpoint
        """
        self.rag = rag_pipeline
        
        print(f"Loading model from {model_path}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            dtype=torch.float16,
            device_map="auto"
        )
        self.model.eval()
        print("Model loaded successfully!\n")
    
    def generate_answer(self, query: str, context: str, primary_ref: str) -> str:
        """
        Generate answer using LLM
        
        Args:
            query: User's question
            context: Retrieved context from RAG
            primary_ref: Primary reference (e.g., "Điều 6 khoản 3")
            
        Returns:
            Generated answer
        """
        # Structured system message with strict rules
        system_message = """Bạn là trợ lý tư vấn pháp luật giao thông Việt Nam.
Hãy trả lời câu hỏi dựa CHÍNH XÁC trên thông tin được cung cấp.

QUY TẮC BẮT BUỘC:
- PHẢI sao chép CHÍNH XÁC số tiền, số điểm, số tháng từ thông tin được cung cấp
- PHẢI nêu ĐẦY ĐỦ: mức phạt tiền + trừ điểm (nếu có) + tước bằng (nếu có)
- KHÔNG bỏ sót bất kỳ hình phạt nào
- KHÔNG tự ý thay đổi con số
- Trả lời ngắn gọn 2-3 câu"""
        
        # Chat template format
        prompt = f"""<|im_start|>system
{system_message}<|im_end|>
<|im_start|>user
Câu hỏi: {query}

{context}<|im_end|>
<|im_start|>assistant
Theo {primary_ref}:"""
        
        # Tokenize and generate
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=150,
                temperature=0.1,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.05,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode and extract assistant response
        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
        
        # Extract only the assistant's response
        if "<|im_start|>assistant" in full_response:
            answer = full_response.split("<|im_start|>assistant")[-1]
            answer = answer.split("<|im_end|>")[0].strip()
            # Remove the "Theo X:" prefix if it's duplicated
            if answer.startswith(f"Theo {primary_ref}:"):
                answer = answer[len(f"Theo {primary_ref}:"):].strip()
        else:
            answer = full_response.strip()
        
        return answer
    
    def query(self, question: str, verbose: bool = False) -> dict:
        """
        Query RAG and generate answer with LLM
        
        Args:
            question: User's question
            verbose: Whether to print debug info
            
        Returns:
            Dictionary with RAG results and generated answer
        """
        # Retrieve from RAG
        rag_result = self.rag.retrieve(question, verbose=verbose)
        
        if rag_result["status"] != "success":
            return {
                "status": "error",
                "message": rag_result.get("message", "Không tìm thấy thông tin"),
                "query": question
            }
        
        # Prepare context for LLM
        primary = rag_result["primary_chunk"]
        
        # Format context based on query type
        if rag_result.get("query_type") == "concept":
            # For concept queries, show definition
            context = f"""Thông tin từ {primary['reference']}:

{primary['content']}"""
        else:
            # For penalty queries, show full details
            context_parts = [f"Thông tin từ {primary['reference']}:\n"]
            context_parts.append(primary['content'])
            
            if primary.get('penalty'):
                context_parts.append(f"\nMức phạt: {primary['penalty']['text']}")
            
            if primary.get('point_deduction'):
                context_parts.append(f"Trừ điểm: {primary['point_deduction']} điểm")
            
            if primary.get('license_revocation'):
                context_parts.append(f"Tước bằng: {primary['license_revocation']}")
            
            context = "\n".join(context_parts)
        
        # Generate answer
        answer = self.generate_answer(question, context, primary['reference'])
        
        return {
            "status": "success",
            "query": question,
            "rag_result": rag_result,
            "generated_answer": answer
        }


def main():
    """Test RAG with LLM"""
    
    print("="*80)
    print("RAG + LLM TEST FOR ND168 + LUẬT TTATGTĐB")
    print("="*80)
    print()
    
    # Initialize RAG
    print("Initializing RAG pipeline...")
    rag = TrafficLawRAG2Laws()
    
    # Initialize LLM
    model_path = r"D:\crawl_law\qwen3-0.6B-instruct-trafficlaws\checkpoint-13176"
    rag_llm = RAGWithLLM(rag, model_path)
    
    # Test queries
    test_queries = [
        # "Xe ô tô vượt đèn đỏ gây tai nạn bị phạt bao nhiêu?",
        # "Người tham gia giao thông là gì?",
        # "Xe máy chạy quá tốc độ 20km/h bị phạt sao?",
        # "Người ngồi ghế sau có phải thắt dây an toàn không?",
        "Xe ô tô đua xe bị phạt bao nhiêu?"
    ]
    
    print("\n" + "="*80)
    print("TESTING WITH LLM GENERATION")
    print("="*80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{len(test_queries)}")
        print(f"{'='*80}")
        print(f"Query: {query}")
        print()
        
        result = rag_llm.query(query, verbose=True)
        
        if result["status"] == "success":
            primary = result["rag_result"]["primary_chunk"]
            answer = result["generated_answer"]
            
            print(f"\n📍 Retrieved: {primary['reference']}")
            
            if result["rag_result"].get("query_type") == "concept":
                print(f"   Type: CONCEPT/RULE")
                print(f"   Content: {primary['content'][:150]}...")
            else:
                if primary.get('penalty'):
                    print(f"   Penalty: {primary['penalty']['text']}")
                if primary.get('point_deduction'):
                    print(f"   Points: {primary['point_deduction']} điểm")
                if primary.get('license_revocation'):
                    print(f"   License revocation: {primary['license_revocation']}")
            
            print(f"\n💬 Generated Answer:")
            print(f"   {answer}")
        else:
            print(f"\n✗ Error: {result['message']}")
    
    print(f"\n{'='*80}")
    print("Testing complete!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
