#!/usr/bin/env python3
"""
Script để test tốc độ token/s của model
"""

import time
import torch
from inference import load_model, tokenizer, model, device

def test_token_speed():
    """Test tốc độ token/s của model"""
    
    # Load model nếu chưa load
    if not load_model():
        print("Không thể load model!")
        return
    
    # Import lại để đảm bảo có tokenizer và model
    from inference import tokenizer, model, device
    
    # Test prompt
    test_prompt = "Hãy giải thích về quyền lao động tại Việt Nam"
    
    print(f"Testing với prompt: '{test_prompt}'")
    print(f"Device: {device}")
    print("-" * 50)
    
    # Đo thời gian và token
    start_time = time.time()
    
    # Tokenize input
    inputs = tokenizer([test_prompt], return_tensors="pt").to(device)
    input_tokens = inputs['input_ids'].shape[1]
    
    print(f"Input tokens: {input_tokens}")
    
    # Generate
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=100,  # Giới hạn để test nhanh
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            num_beams=1,
        )
    
    end_time = time.time()
    
    # Tính toán
    total_tokens = output.shape[1] - input_tokens
    elapsed_time = end_time - start_time
    tokens_per_second = total_tokens / elapsed_time
    
    # Decode output
    generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
    answer = generated_text.split(test_prompt, 1)[-1].strip() if test_prompt in generated_text else generated_text
    
    print(f"Generated tokens: {total_tokens}")
    print(f"Time elapsed: {elapsed_time:.2f} seconds")
    print(f"Speed: {tokens_per_second:.2f} tokens/second")
    print(f"Speed: {tokens_per_second * 60:.2f} tokens/minute")
    print("-" * 50)
    print(f"Generated text: {answer[:200]}...")
    
    return tokens_per_second

def test_streaming_speed():
    """Test tốc độ streaming"""
    
    if not load_model():
        print("Không thể load model!")
        return
    
    # Import lại để đảm bảo có tokenizer
    from inference import tokenizer, get_answer_stream
    
    test_prompt = "Hãy giải thích về quyền lao động tại Việt Nam"
    
    print(f"Testing streaming với prompt: '{test_prompt}'")
    print("-" * 50)
    
    start_time = time.time()
    token_count = 0
    
    for chunk in get_answer_stream(test_prompt):
        # Đếm token trong chunk
        if chunk is not None:
            new_tokens = tokenizer.encode(chunk, add_special_tokens=False)
            token_count += len(new_tokens)
            
            # In ra chunk đầu tiên với thông tin tốc độ
            if token_count <= len(new_tokens):
                elapsed_time = time.time() - start_time
                if elapsed_time > 0:
                    tokens_per_second = token_count / elapsed_time
                    print(f"[Tốc độ: {tokens_per_second:.2f} token/s] {chunk}", end="", flush=True)
                else:
                    print(chunk, end="", flush=True)
            else:
                print(chunk, end="", flush=True)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n\nTổng kết:")
    print(f"Total tokens: {token_count}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average speed: {token_count / total_time:.2f} tokens/second")

if __name__ == "__main__":
    print("=== SPEED TEST FOR TOKEN GENERATION ===")
    print()
    
    # Test 1: Non-streaming
    print("1. Testing non-streaming generation:")
    speed1 = test_token_speed()
    print()
    
    # Test 2: Streaming
    print("2. Testing streaming generation:")
    from inference import get_answer_stream
    test_streaming_speed()
    print()
    
    print("=== TEST COMPLETED ===")
