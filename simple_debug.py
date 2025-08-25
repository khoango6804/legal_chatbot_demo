#!/usr/bin/env python3
"""
Simple debug script
"""

import time
from inference import get_answer_stream

def simple_debug():
    test_question = "Những yêu cầu để có một hợp đồng hợp lệ là gì?"
    
    print(f"Testing: '{test_question}'")
    print("-" * 50)
    
    start_time = time.time()
    token_count = 0
    first_chunk = True
    
    for chunk in get_answer_stream(test_question):
        # Đếm token
        estimated_tokens = len(chunk.encode('utf-8')) // 4
        token_count += estimated_tokens
        
        # Tính thời gian
        elapsed_time = time.time() - start_time
        
        print(f"Chunk: {len(chunk)} chars, {estimated_tokens} tokens, {elapsed_time:.3f}s, total_tokens: {token_count}")
        
        # Kiểm tra điều kiện
        if elapsed_time > 0.3 and token_count > 3:
            tokens_per_second = token_count / elapsed_time
            print(f"  -> Điều kiện OK! Tốc độ: {tokens_per_second:.2f} token/s")
            if first_chunk:
                print(f"  -> FIRST CHUNK! Sẽ hiển thị tốc độ")
                first_chunk = False
        else:
            print(f"  -> Điều kiện chưa OK (time: {elapsed_time:.3f} > 0.3? {elapsed_time > 0.3}, tokens: {token_count} > 3? {token_count > 3})")
        
        if len(chunk) > 0:
            print(f"  Content: {chunk[:30]}...")
        
        # Chỉ test 10 chunk đầu
        if token_count > 20:
            break
    
    print("-" * 50)
    print(f"Final: {token_count} tokens in {elapsed_time:.2f}s = {token_count/elapsed_time:.2f} token/s")

if __name__ == "__main__":
    simple_debug()
