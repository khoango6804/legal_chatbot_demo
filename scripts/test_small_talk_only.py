#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test only small talk questions
"""
import requests
import time

SMALL_TALK_QUESTIONS = [
    "sử dụng điện thoại khi lái xe",
    "nghe điện thoại khi đang điều khiển xe máy",
    "dùng điện thoại khi lái ô tô",
    "không bật đèn khi đi ban đêm",
    "không bật xi-nhan khi rẽ",
    "lấn làn khi vượt",
    "bỏ chạy sau khi gây tai nạn",
]

def test_question(question: str, url: str = "http://127.0.0.1:8100/chat"):
    payload = {"question": question}
    try:
        response = requests.post(url, json=payload, timeout=60, stream=True)
        if response.status_code == 200:
            answer_parts = []
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    answer_parts.append(chunk)
            full_response = "".join(answer_parts)
            
            if "[" in full_response:
                answer = full_response.rsplit("[", 1)[0].strip()
            else:
                answer = full_response
            
            is_small_talk = "Mình là trợ lý pháp luật giao thông" in answer
            has_legal_info = "Điều" in answer or "khoản" in answer or "phạt" in answer.lower()
            
            return {
                "question": question,
                "answer": answer[:200],
                "is_small_talk": is_small_talk,
                "has_legal_info": has_legal_info,
                "status": "small_talk" if is_small_talk else ("success" if has_legal_info else "unknown")
            }
    except Exception as e:
        return {"question": question, "error": str(e)[:100]}

def main():
    url = "http://127.0.0.1:8100/chat"
    
    print("="*80)
    print("Testing Small Talk Questions")
    print("="*80)
    
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
    
    print(f"Testing {len(SMALL_TALK_QUESTIONS)} questions...\n")
    
    for i, question in enumerate(SMALL_TALK_QUESTIONS, 1):
        print(f"[{i}/{len(SMALL_TALK_QUESTIONS)}] {question}")
        result = test_question(question, url)
        
        if "error" in result:
            print(f"  ✗ ERROR: {result['error']}\n")
        elif result.get("is_small_talk"):
            print(f"  ✗ STILL SMALL TALK")
            print(f"  Answer: {result['answer'][:100]}...\n")
        elif result.get("has_legal_info"):
            print(f"  ✓ FIXED - Has legal info")
            print(f"  Answer: {result['answer'][:100]}...\n")
        else:
            print(f"  ? Unknown response")
            print(f"  Answer: {result['answer'][:100]}...\n")
        
        time.sleep(0.2)

if __name__ == "__main__":
    main()

