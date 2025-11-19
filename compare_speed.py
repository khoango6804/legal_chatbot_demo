#!/usr/bin/env python3
"""
Script so sánh tốc độ báo cáo với tốc độ thực tế
"""

import time
from inference import get_answer_stream

def compare_speed():
    test_question = "Những yêu cầu để có một hợp đồng hợp lệ là gì?"
    
    print(f"Testing: '{test_question}'")
    print("-" * 60)
    
    # Test 1: Đo tốc độ thực tế
    print("1. Đo tốc độ thực tế:")
    start_time = time.time()
    token_count = 0
    first_token_time = None
    
    for chunk in get_answer_stream(test_question):
        estimated_tokens = len(chunk.encode('utf-8')) // 4
        token_count += estimated_tokens
        
        # Ghi nhận thời điểm token đầu tiên
        if first_token_time is None and estimated_tokens > 0:
            first_token_time = time.time()
            print(f"   Thời điểm token đầu tiên: {first_token_time - start_time:.2f}s")
        
        # In ra chunk đầu tiên có nội dung
        if token_count <= estimated_tokens and len(chunk.strip()) > 0:
            print(f"   Chunk đầu tiên: '{chunk[:50]}...'")
            break
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"   Tổng thời gian: {total_time:.2f}s")
    print(f"   Tổng tokens: {token_count}")
    
    if first_token_time is not None:
        generation_time = end_time - first_token_time
        if generation_time > 0:
            actual_speed = token_count / generation_time
            print(f"   Thời gian generation: {generation_time:.2f}s")
            print(f"   Tốc độ thực tế: {actual_speed:.2f} token/s")
        else:
            print(f"   Thời gian generation: {generation_time:.2f}s (quá ngắn)")
            print(f"   Tốc độ thực tế: {token_count / total_time:.2f} token/s")
    else:
        print(f"   Tốc độ thực tế: {token_count / total_time:.2f} token/s")
    
    print()
    
    # Test 2: Đo tốc độ báo cáo
    print("2. Đo tốc độ báo cáo:")
    response = ""
    for chunk in get_answer_stream(test_question):
        response += chunk
    
    if "[Tốc độ:" in response:
        start_idx = response.find("[Tốc độ:")
        end_idx = response.find("token/s]")
        if start_idx != -1 and end_idx != -1:
            speed_info = response[start_idx:end_idx + 8]
            reported_speed = float(speed_info.split(": ")[1].split(" ")[0])
            print(f"   Tốc độ báo cáo: {reported_speed:.2f} token/s")
            print(f"   Thông tin hiển thị: {speed_info}")
        else:
            print("   Không tìm thấy thông tin tốc độ")
    else:
        print("   Không có thông tin tốc độ")
    
    print("-" * 60)
    print("Kết luận:")
    if first_token_time is not None:
        generation_time = end_time - first_token_time
        if generation_time > 0:
            actual_speed = token_count / generation_time
            print(f"Tốc độ thực tế: {actual_speed:.2f} token/s")
            print(f"Tốc độ báo cáo: {reported_speed:.2f} token/s")
            
            if abs(actual_speed - reported_speed) < 2:
                print("Tốc độ báo cáo chính xác!")
            else:
                print("Có sự khác biệt giữa tốc độ thực tế và báo cáo")
        else:
            print("Không thể tính toán tốc độ chính xác (thời gian quá ngắn)")
    else:
        print("Không thể tính toán tốc độ thực tế")

if __name__ == "__main__":
    compare_speed()
