#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to query backend with 100 diverse traffic law questions
Handles streaming response from /chat endpoint
"""
import requests
import time
import json
from typing import List, Dict

# 100 diverse questions covering various traffic law scenarios
TEST_QUESTIONS = [
    # Đèn tín hiệu
    "xe máy vượt đèn đỏ thì sao",
    "xe máy vượt đèn đỏ bị phạt bao nhiêu",
    "ô tô vượt đèn đỏ phạt như thế nào",
    "vượt đèn đỏ bằng xe máy sẽ bị phạt thế nào",
    "không chấp hành tín hiệu đèn giao thông",
    
    # Đua xe
    "xe máy đua xe bị phạt gì",
    "đua xe máy phạt bao nhiêu",
    "ô tô đua xe bị phạt như thế nào",
    "tổ chức đua xe trái phép",
    "cổ vũ đua xe trái phép",
    
    # Tốc độ
    "xe máy chạy quá tốc độ 60km/h",
    "ô tô vượt tốc độ 80km/h",
    "chạy quá tốc độ 100km/h",
    "xe máy chạy quá tốc độ gây tai nạn",
    "vượt tốc độ trong khu vực đông dân cư",
    
    # Mũ bảo hiểm
    "không đội mũ bảo hiểm",
    "xe máy không đội mũ bảo hiểm phạt bao nhiêu",
    "chỉ có một mũ bảo hiểm",
    "người ngồi sau không đội mũ",
    
    # Điện thoại
    "sử dụng điện thoại khi lái xe",
    "nghe điện thoại khi đang điều khiển xe máy",
    "dùng điện thoại khi lái ô tô",
    
    # Rẽ, quay đầu
    "rẽ phải không đúng quy định",
    "rẽ trái không đúng nơi quy định",
    "quay đầu xe sai quy định",
    "quay đầu xe ở nơi cấm",
    
    # Chuyển làn
    "chuyển làn không đúng quy định",
    "chuyển làn không bật xi-nhan",
    "đổi làn gây nguy hiểm",
    
    # Cán vạch
    "cán vạch phân làn",
    "cán vạch kẻ đường",
    "đi cán lên vạch",
    
    # Dừng đỗ sai
    "dừng xe sai quy định",
    "đỗ xe ở làn khẩn cấp",
    "đậu xe chắn cửa nhà",
    "dừng xe ở nơi cấm",
    
    # Đường cấm
    "đi vào đường cấm",
    "xe máy đi vào khu vực cấm",
    "ô tô đi vào làn buýt",
    
    # Giấy tờ
    "không có bằng lái xe",
    "không mang bằng lái xe",
    "bằng lái xe hết hạn",
    "không có giấy đăng ký xe",
    "không có bảo hiểm xe",
    
    # Đèn xe
    "không bật đèn khi đi ban đêm",
    "không bật xi-nhan khi rẽ",
    "sử dụng đèn pha trong thành phố",
    "đèn chiếu xa gây chói mắt",
    
    # Dây an toàn
    "không thắt dây an toàn",
    "người ngồi sau không thắt dây an toàn",
    
    # Vượt ẩu
    "vượt ẩu gây nguy hiểm",
    "lấn làn khi vượt",
    "vượt không đúng quy định",
    
    # Ngược chiều
    "đi ngược chiều",
    "đi vào đường ngược chiều",
    "lấn sang làn ngược chiều",
    
    # Tải trọng
    "chở quá tải",
    "chở quá số người quy định",
    "xe máy chở 3 người",
    "ô tô chở quá số người",
    
    # Hàng hóa
    "chở hàng quá khổ",
    "chở hàng không đúng quy định",
    "chở hàng nguy hiểm",
    
    # Rượu bia
    "uống rượu bia lái xe",
    "nồng độ cồn vượt quá",
    "say rượu lái xe",
    
    # Tai nạn
    "gây tai nạn giao thông",
    "bỏ chạy sau khi gây tai nạn",
    "không cứu giúp người bị nạn",
    
    # Trẻ em
    "chở trẻ em không đúng quy định",
    "trẻ em ngồi ghế trước",
    
    # Xe đạp
    "xe đạp đi sai làn",
    "xe đạp không chấp hành đèn tín hiệu",
    
    # Xe tải
    "xe tải đi vào đường cấm",
    "xe tải chở quá tải",
    
    # Xe buýt
    "xe buýt dừng sai quy định",
    "xe buýt không nhường đường",
    
    # Khu vực đông dân cư
    "chạy quá tốc độ trong khu vực đông dân cư",
    "bấm còi trong khu vực đông dân cư",
    
    # Đường cao tốc
    "dừng xe trên đường cao tốc",
    "quay đầu trên đường cao tốc",
    
    # Đường hẹp
    "không nhường đường trên đường hẹp",
    "đi sai làn trên đường hẹp",
    
    # Giao lộ
    "không nhường đường tại giao lộ",
    "vượt tại giao lộ",
    
    # Cầu, hầm
    "dừng xe trên cầu",
    "quay đầu trong hầm",
    
    # Đường một chiều
    "đi ngược chiều đường một chiều",
    "quay đầu trên đường một chiều",
    
    # Làn ưu tiên
    "đi vào làn ưu tiên",
    "không nhường làn ưu tiên",
    
    # Xe cứu thương
    "không nhường đường xe cứu thương",
    "chặn đường xe cứu thương",
    
    # Xe công vụ
    "không nhường đường xe công vụ",
    
    # Xe đạp điện
    "xe đạp điện đi sai làn",
    "xe đạp điện không đội mũ",
    
    # Xe máy điện
    "xe máy điện chạy quá tốc độ",
    "xe máy điện không có giấy tờ",
    
    # Tổ chức
    "tổ chức vi phạm giao thông",
    "doanh nghiệp vi phạm vận tải",
    
    # Vận tải
    "xe vận tải chở quá tải",
    "xe vận tải không có giấy phép",
    
    # Khác
    "mở cửa xe không đúng quy định",
    "bấm còi liên tục",
    "xả rác từ xe",
    "không chấp hành hiệu lệnh cảnh sát",
]

def test_question(question: str, url: str = "http://127.0.0.1:8100/chat") -> Dict:
    """Test a single question and return result - handles streaming response"""
    payload = {"question": question}
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=60, stream=True)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            # Read streaming response
            answer_parts = []
            stats_line = ""
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    answer_parts.append(chunk)
            
            full_response = "".join(answer_parts)
            
            # Extract answer and stats
            if "[" in full_response and "]" in full_response:
                # Split answer and stats
                parts = full_response.rsplit("[", 1)
                if len(parts) == 2:
                    answer = parts[0].strip()
                    stats_line = "[" + parts[1]
                else:
                    answer = full_response
            else:
                answer = full_response
            
            # Parse stats if available
            source = ""
            tokens = 0
            if stats_line:
                # Try to extract source and tokens from stats
                if "Source:" in stats_line:
                    try:
                        source_part = stats_line.split("Source:")[1].split("]")[0].strip()
                        source = source_part
                    except:
                        pass
                if "Output tokens:" in stats_line:
                    try:
                        tokens_part = stats_line.split("Output tokens:")[1].split()[0]
                        tokens = int(tokens_part)
                    except:
                        pass
            
            return {
                "question": question,
                "status": "success",
                "answer": answer[:500],  # Limit answer length
                "source": source,
                "time": elapsed,
                "tokens": tokens,
                "full_response": full_response[:200]  # For debugging
            }
        else:
            return {
                "question": question,
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text[:100] if hasattr(response, 'text') else 'No response'}",
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
    print("Testing 100 traffic law questions")
    print("=" * 80)
    print(f"Backend URL: {url}\n")
    
    # Wait for backend to be ready
    print("Waiting for backend to be ready...")
    max_wait = 60
    waited = 0
    while waited < max_wait:
        try:
            response = requests.get(url.replace("/chat", "/"), timeout=5)
            if response.status_code == 200:
                print("Backend is ready!\n")
                break
        except:
            pass
        time.sleep(2)
        waited += 2
        if waited % 10 == 0:
            print(f"  Waiting... ({waited}s/{max_wait}s)")
    
    if waited >= max_wait:
        print("ERROR: Backend not responding. Please check if backend is running.")
        return
    
    results = []
    total_time = 0
    success_count = 0
    error_count = 0
    
    print(f"Starting tests...\n")
    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"[{i:3d}/100] Testing: {question[:50]}...", end=" ", flush=True)
        result = test_question(question, url)
        results.append(result)
        
        if result["status"] == "success":
            success_count += 1
            total_time += result["time"]
            answer_preview = result["answer"][:40].replace("\n", " ")
            print(f"✓ ({result['time']:.2f}s) - {answer_preview}...")
        else:
            error_count += 1
            error_msg = result.get("error", "Unknown")[:50]
            print(f"✗ ERROR: {error_msg}")
        
        # Small delay to avoid overwhelming the server
        time.sleep(0.2)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total questions: {len(TEST_QUESTIONS)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    if success_count > 0:
        print(f"Average response time: {total_time/success_count:.2f}s")
        print(f"Total time: {total_time:.2f}s")
    
    # Save results
    output_file = "test_100_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {output_file}")
    
    # Show some sample answers
    print("\n" + "=" * 80)
    print("SAMPLE ANSWERS (first 5 successful)")
    print("=" * 80)
    shown = 0
    for result in results:
        if result["status"] == "success" and shown < 5:
            print(f"\nQ: {result['question']}")
            print(f"A: {result['answer'][:300]}...")
            if result.get('source'):
                print(f"Source: {result['source']}")
            shown += 1

if __name__ == "__main__":
    main()

