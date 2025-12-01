#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify fixes for previously failed questions
"""
import requests
import time
import json

# Các câu hỏi trước đây bị lỗi
FAILED_QUESTIONS = [
    # Bị chặn bởi guardrail (out_of_scope)
    "cán vạch phân làn",
    "cán vạch kẻ đường",
    "đi cán lên vạch",
    "đi vào đường cấm",
    "đi ngược chiều",
    "chở quá tải",
    "chở hàng quá khổ",
    "chở hàng nguy hiểm",
    "vượt tại giao lộ",
    "quay đầu trong hầm",
    "bấm còi liên tục",
    
    # Trả về small talk response
    "sử dụng điện thoại khi lái xe",
    "nghe điện thoại khi đang điều khiển xe máy",
    "dùng điện thoại khi lái ô tô",
    "không bật đèn khi đi ban đêm",
    "không bật xi-nhan khi rẽ",
    "lấn làn khi vượt",
    "bỏ chạy sau khi gây tai nạn",
]

def test_question(question: str, url: str = "http://127.0.0.1:8100/chat") -> dict:
    """Test a single question and return result"""
    payload = {"question": question}
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=60, stream=True)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            answer_parts = []
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    answer_parts.append(chunk)
            
            full_response = "".join(answer_parts)
            
            # Extract answer and stats
            if "[" in full_response and "]" in full_response:
                parts = full_response.rsplit("[", 1)
                if len(parts) == 2:
                    answer = parts[0].strip()
                    stats_line = "[" + parts[1]
                else:
                    answer = full_response
            else:
                answer = full_response
            
            # Check if it's a guardrail response
            is_guardrail = False
            is_small_talk = False
            if "Xin lỗi, mình chỉ hỗ trợ" in answer:
                is_guardrail = True
            if "Mình là trợ lý pháp luật giao thông" in answer:
                is_small_talk = True
            
            return {
                "question": question,
                "status": "success",
                "answer": answer[:300],
                "time": elapsed,
                "is_guardrail": is_guardrail,
                "is_small_talk": is_small_talk,
                "has_legal_info": "Điều" in answer or "khoản" in answer or "phạt" in answer.lower(),
            }
        else:
            return {
                "question": question,
                "status": "error",
                "error": f"HTTP {response.status_code}",
                "time": elapsed
            }
    except Exception as e:
        return {
            "question": question,
            "status": "error",
            "error": str(e)[:200],
            "time": 0
        }

def main():
    url = "http://127.0.0.1:8100/chat"
    
    print("=" * 80)
    print("Testing previously failed questions")
    print("=" * 80)
    print(f"Backend URL: {url}\n")
    
    # Wait for backend
    print("Waiting for backend...")
    for i in range(15):
        try:
            response = requests.get(url.replace("/chat", "/"), timeout=2)
            if response.status_code == 200:
                print("Backend is ready!\n")
                break
        except:
            pass
        time.sleep(2)
        if i < 14:
            print(f"  Waiting... ({i*2+2}s)")
    
    results = []
    fixed_count = 0
    still_failed_count = 0
    
    print(f"Testing {len(FAILED_QUESTIONS)} questions...\n")
    for i, question in enumerate(FAILED_QUESTIONS, 1):
        print(f"[{i:2d}/{len(FAILED_QUESTIONS)}] {question[:50]:<50}", end=" ", flush=True)
        result = test_question(question, url)
        results.append(result)
        
        if result["status"] == "success":
            if result.get("is_guardrail"):
                print("✗ STILL BLOCKED (guardrail)")
                still_failed_count += 1
            elif result.get("is_small_talk"):
                print("✗ STILL SMALL TALK")
                still_failed_count += 1
            elif result.get("has_legal_info"):
                print("✓ FIXED (has legal info)")
                fixed_count += 1
            else:
                print("? UNKNOWN (no legal info but not blocked)")
                still_failed_count += 1
        else:
            print(f"✗ ERROR: {result.get('error', 'Unknown')}")
            still_failed_count += 1
        
        time.sleep(0.2)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total questions: {len(FAILED_QUESTIONS)}")
    print(f"Fixed: {fixed_count}")
    print(f"Still failed: {still_failed_count}")
    print(f"Success rate: {fixed_count/len(FAILED_QUESTIONS)*100:.1f}%")
    
    # Show details
    print("\n" + "=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    for result in results:
        status_icon = "✓" if result.get("has_legal_info") else "✗"
        guardrail_note = " [GUARDRAIL]" if result.get("is_guardrail") else ""
        smalltalk_note = " [SMALL TALK]" if result.get("is_small_talk") else ""
        print(f"\n{status_icon} {result['question']}{guardrail_note}{smalltalk_note}")
        print(f"   Answer: {result.get('answer', 'N/A')[:150]}...")

if __name__ == "__main__":
    main()

