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

# 100 test questions provided by user (đa dạng hành vi, dùng để regression test)
TEST_QUESTIONS = [
    "Xe máy vượt đèn đỏ bị phạt bao nhiêu?",
    "Ô tô vượt đèn đỏ thì bị xử phạt thế nào?",
    "Không chấp hành tín hiệu đèn giao thông thì bị phạt ra sao?",
    "Xe máy chạy quá tốc độ 10km/h bị phạt bao nhiêu?",
    "Xe máy chạy quá tốc độ 20km/h bị phạt bao nhiêu?",
    "Xe máy chạy quá tốc độ 30km/h bị phạt thế nào?",
    "Ô tô chạy quá tốc độ 10km/h bị phạt bao nhiêu?",
    "Ô tô chạy quá tốc độ 20km/h bị phạt bao nhiêu?",
    "Ô tô chạy quá tốc độ 35km/h thì bị xử phạt ra sao?",
    "Đi vào đường cấm bằng xe máy bị phạt bao nhiêu?",
    "Ô tô đi vào đường cấm thì phạt thế nào?",
    "Đi ngược chiều trên đường một chiều bị xử phạt ra sao?",
    "Xe máy đi ngược chiều trên đường có biển cấm đi ngược chiều thì bị phạt bao nhiêu?",
    "Lấn làn khi vượt xe bị xử phạt thế nào?",
    "Đi sai làn đường quy định đối với xe máy thì phạt bao nhiêu?",
    "Ô tô đi sai làn đường bị phạt thế nào?",
    "Cán vạch kẻ đường liên tục khi điều khiển xe máy bị phạt bao nhiêu?",
    "Vượt xe trên đoạn đường có vạch liền có bị phạt không?",
    "Không đội mũ bảo hiểm khi đi xe máy bị phạt bao nhiêu?",
    "Đội mũ bảo hiểm nhưng không cài quai có bị phạt không, phạt bao nhiêu?",
    "Chở 3 người trên xe máy thì bị xử phạt thế nào?",
    "Chở 4 người trên xe máy bị phạt bao nhiêu?",
    "Chở người không đội mũ bảo hiểm khi đi xe máy bị phạt như thế nào?",
    "Xe máy chở hàng cồng kềnh bị phạt bao nhiêu?",
    "Xe máy chở hàng vượt quá chiều rộng quy định thì bị phạt thế nào?",
    "Ô tô chở quá tải trọng 20% bị phạt bao nhiêu?",
    "Ô tô chở quá tải trên 50% thì bị xử phạt ra sao?",
    "Xe tải chở hàng quá khổ giới hạn cầu đường thì bị phạt thế nào?",
    "Chở hàng nguy hiểm mà không có giấy phép bị phạt bao nhiêu?",
    "Sử dụng điện thoại khi đang lái xe ô tô bị phạt thế nào?",
    "Nghe điện thoại khi điều khiển xe máy bị phạt bao nhiêu?",
    "Dùng điện thoại nhắn tin khi lái ô tô bị phạt ra sao?",
    "Không bật đèn chiếu sáng khi đi ban đêm bằng ô tô bị phạt bao nhiêu?",
    "Xe máy không bật đèn khi đi ban đêm thì phạt thế nào?",
    "Bật đèn pha trong khu đô thị, khu đông dân cư có bị phạt không?",
    "Không bật xi nhan khi rẽ phải bằng xe máy bị phạt bao nhiêu?",
    "Không bật đèn báo rẽ khi chuyển làn bằng ô tô bị phạt thế nào?",
    "Chuyển làn không đúng nơi cho phép bị xử phạt ra sao?",
    "Quay đầu xe ở nơi có biển cấm quay đầu thì phạt thế nào?",
    "Quay đầu xe trong hầm đường bộ bị phạt bao nhiêu?",
    "Dừng xe ô tô trên phần đường dành cho người đi bộ bị phạt thế nào?",
    "Đỗ xe nơi có biển “Cấm dừng, cấm đỗ” bị xử phạt ra sao?",
    "Dừng xe trên cầu gây cản trở giao thông bị phạt bao nhiêu?",
    "Đỗ xe chiếm một phần đường xe chạy gây ùn tắc thì phạt thế nào?",
    "Không tuân thủ vạch dừng khi có đèn đỏ bị phạt bao nhiêu?",
    "Vượt xe tại nơi đường giao nhau bị phạt thế nào?",
    "Vượt xe trong hầm đường bộ bị xử phạt ra sao?",
    "Không nhường đường cho xe ưu tiên đang phát tín hiệu bị phạt bao nhiêu?",
    "Bấm còi, rú ga liên tục trong khu dân cư bị phạt thế nào?",
    "Bấm còi trong khoảng thời gian bị cấm có bị phạt không, phạt bao nhiêu?",
    "Không mang theo giấy phép lái xe khi điều khiển xe máy bị phạt bao nhiêu?",
    "Không có giấy phép lái xe nhưng vẫn lái xe máy thì bị xử phạt thế nào?",
    "Không có bằng lái ô tô nhưng vẫn điều khiển xe ô tô bị phạt ra sao?",
    "Không mang đăng ký xe khi lưu thông bị phạt bao nhiêu?",
    "Không có bảo hiểm trách nhiệm dân sự bắt buộc bị phạt bao nhiêu?",
    "Giấy đăng kiểm ô tô hết hạn mà vẫn tham gia giao thông thì bị phạt thế nào?",
    "Không thắt dây an toàn khi ngồi ghế trước trên ô tô bị phạt bao nhiêu?",
    "Hành khách ngồi ghế sau không thắt dây an toàn có bị phạt không?",
    "Cho người không đủ điều kiện điều khiển xe tham gia giao thông bị phạt thế nào?",
    "Giao xe cho người chưa đủ tuổi lái xe máy thì bị xử phạt ra sao?",
    "Uống rượu bia rồi lái xe máy bị phạt bao nhiêu?",
    "Nồng độ cồn vượt quá 50mg/100ml máu khi lái xe máy bị phạt thế nào?",
    "Lái ô tô có nồng độ cồn vượt quá mức cao nhất thì bị xử phạt ra sao?",
    "Vừa uống bia vừa lái ô tô trên đường cao tốc bị phạt bao nhiêu?",
    "Sử dụng ma túy khi điều khiển xe bị phạt như thế nào?",
    "Từ chối kiểm tra nồng độ cồn khi bị CSGT dừng xe thì bị phạt ra sao?",
    "Gây tai nạn giao thông nhưng không dừng lại, không giữ nguyên hiện trường bị phạt bao nhiêu?",
    "Bỏ chạy sau khi gây tai nạn giao thông bị xử phạt thế nào?",
    "Không cứu giúp người bị nạn khi có khả năng mà vẫn bỏ đi bị phạt ra sao?",
    "Gây tai nạn rồi không cung cấp thông tin, không hợp tác với cơ quan chức năng thì bị phạt thế nào?",
    "Đi xe máy vào đường cao tốc bị phạt bao nhiêu?",
    "Đi bộ trên đường cao tốc có bị phạt không, phạt thế nào?",
    "Lùi xe trên đường cao tốc bị xử phạt ra sao?",
    "Quay đầu xe trên đường cao tốc bị phạt thế nào?",
    "Dừng xe, đỗ xe trên làn dừng khẩn cấp khi không có sự cố bị phạt bao nhiêu?",
    "Không giữ khoảng cách an toàn trên đường cao tốc bị phạt thế nào?",
    "Không tuân thủ tốc độ tối thiểu trên đường cao tốc thì bị xử phạt ra sao?",
    "Đi xe máy vào hầm vượt sông dành riêng cho ô tô bị phạt bao nhiêu?",
    "Không nhường đường cho người đi bộ trên phần đường dành riêng thì phạt thế nào?",
    "Chạy xe trên vỉa hè dành cho người đi bộ bị xử phạt ra sao?",
    "Xe máy bật còi inh ỏi gần bệnh viện, trường học bị phạt bao nhiêu?",
    "Ô tô chở quá số người quy định thì bị phạt thế nào?",
    "Xe khách đón trả khách không đúng nơi quy định bị xử phạt ra sao?",
    "Xe taxi dừng đỗ đón khách dưới lòng đường gây cản trở giao thông bị phạt bao nhiêu?",
    "Không chấp hành hiệu lệnh dừng xe của CSGT bị phạt thế nào?",
    "Tự ý tháo dỡ, làm sai lệch biển báo giao thông bị xử phạt ra sao?",
    "Đua xe trái phép bằng xe máy trên đường bộ bị phạt bao nhiêu?",
    "Tổ chức đua xe trái phép thì bị xử phạt như thế nào?",
    "Bốc đầu xe máy, chạy lạng lách đánh võng trên đường bị phạt bao nhiêu?",
    "Nẹt pô, gây tiếng ồn lớn khi điều khiển xe máy bị phạt thế nào?",
    "Đi xe đạp điện nhưng không đội mũ bảo hiểm có bị phạt không, phạt bao nhiêu?",
    "Người dưới 16 tuổi điều khiển xe máy dưới 50cc bị xử phạt ra sao?",
    "Chở trẻ em dưới 7 tuổi phía sau xe máy mà không đội mũ bảo hiểm thì bị phạt bao nhiêu?",
    "Điều khiển xe khi giấy phép lái xe đã bị tước quyền sử dụng có bị phạt không, phạt thế nào?",
    "Không chấp hành quy định phân luồng giao thông của người điều khiển giao thông thì bị phạt ra sao?",
    "Vượt xe bên phải trên đường không được phép vượt bị xử phạt thế nào?",
    "Dừng xe giữa ngã tư khi có tín hiệu đèn xanh nhấp nháy bị phạt bao nhiêu?",
    "Không bật đèn cảnh báo khi xe bị hỏng nằm trên đường bị phạt thế nào?",
    "Không gắn biển số xe mà vẫn tham gia giao thông thì bị xử phạt ra sao?",
    "Sử dụng biển số giả khi lưu thông trên đường bị phạt bao nhiêu?",
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

