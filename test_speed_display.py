#!/usr/bin/env python3
"""
Test script để kiểm tra hiển thị tốc độ token/s
"""

from inference import get_answer_stream

def test_speed_display():
    """Test hiển thị tốc độ token/s"""
    
    test_question = "Những yêu cầu để có một hợp đồng hợp lệ là gì?"
    
    print(f"Testing với câu hỏi: '{test_question}'")
    print("-" * 60)
    
    response = ""
    for chunk in get_answer_stream(test_question):
        response += chunk
        print(chunk, end="", flush=True)
    
    print("\n" + "-" * 60)
    print("Kết quả:")
    print(f"Tổng độ dài response: {len(response)} ký tự")
    
    # Kiểm tra xem có hiển thị tốc độ không
    if "[Tốc độ:" in response:
        print("✅ Tốc độ token/s đã được hiển thị")
        # Tìm và in ra thông tin tốc độ
        start_idx = response.find("[Tốc độ:")
        end_idx = response.find("token/s]")
        if start_idx != -1 and end_idx != -1:
            speed_info = response[start_idx:end_idx + 8]
            print(f"Thông tin tốc độ: {speed_info}")
    else:
        print("❌ Không tìm thấy thông tin tốc độ")

if __name__ == "__main__":
    test_speed_display()
