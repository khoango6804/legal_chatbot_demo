#!/usr/bin/env python3
"""
Debug script để xem chi tiết quá trình tính toán tốc độ
"""

import time
from inference import get_answer_stream

def debug_speed():
    """Debug quá trình tính toán tốc độ"""
    
    test_question = "Những yêu cầu để có một hợp đồng hợp lệ là gì?"
    
    print(f"Testing với câu hỏi: '{test_question}'")
    print("-" * 60)
    
    start_time = time.time()
    token_count = 0
    chunk_count = 0
    
    for chunk in get_answer_stream(test_question):
        chunk_count += 1
        current_time = time.time()
        elapsed_time = current_time - start_time
        
        # Ước tính token (1 token ≈ 4 ký tự)
        estimated_tokens = len(chunk.encode('utf-8')) // 4
        token_count += estimated_tokens
        
        print(f"Chunk {chunk_count}: {len(chunk)} chars, {estimated_tokens} tokens, {elapsed_time:.3f}s")
        
        if chunk_count <= 5:  # Chỉ in 5 chunk đầu
            print(f"  Content: {chunk[:50]}...")
        
        if elapsed_time > 0.2 and token_count > 2:
            tokens_per_second = token_count / elapsed_time
            print(f"  -> Tốc độ: {tokens_per_second:.2f} token/s")
    
    print("-" * 60)
    print(f"Tổng kết:")
    print(f"Total chunks: {chunk_count}")
    print(f"Total tokens (estimated): {token_count}")
    print(f"Total time: {elapsed_time:.2f} seconds")
    print(f"Average speed: {token_count / elapsed_time:.2f} tokens/second")

if __name__ == "__main__":
    debug_speed()
