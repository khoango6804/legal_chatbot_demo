#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Continuous testing script - tests questions repeatedly and reports results
"""
import requests
import time
import json
from datetime import datetime
from typing import List, Dict

# All test questions
ALL_QUESTIONS = [
    # Đèn tín hiệu
    "xe máy vượt đèn đỏ thì sao",
    "xe máy vượt đèn đỏ bị phạt bao nhiêu",
    
    # Đua xe
    "xe máy đua xe bị phạt gì",
    "đua xe máy phạt bao nhiêu",
    
    # Tốc độ
    "xe máy chạy quá tốc độ 60km/h",
    "ô tô vượt tốc độ 80km/h",
    
    # Mũ bảo hiểm
    "không đội mũ bảo hiểm",
    "xe máy không đội mũ bảo hiểm phạt bao nhiêu",
    
    # Điện thoại
    "sử dụng điện thoại khi lái xe",
    "nghe điện thoại khi đang điều khiển xe máy",
    
    # Rẽ, quay đầu
    "rẽ phải không đúng quy định",
    "quay đầu xe sai quy định",
    
    # Chuyển làn
    "chuyển làn không đúng quy định",
    "chuyển làn không bật xi-nhan",
    
    # Cán vạch
    "cán vạch phân làn",
    "cán vạch kẻ đường",
    
    # Dừng đỗ sai
    "dừng xe sai quy định",
    "đỗ xe ở làn khẩn cấp",
    
    # Đường cấm
    "đi vào đường cấm",
    "xe máy đi vào khu vực cấm",
    
    # Giấy tờ
    "không có bằng lái xe",
    "không mang bằng lái xe",
    
    # Đèn xe
    "không bật đèn khi đi ban đêm",
    "không bật xi-nhan khi rẽ",
    "sử dụng đèn pha trong thành phố",
    
    # Dây an toàn
    "không thắt dây an toàn",
    
    # Vượt ẩu
    "vượt ẩu gây nguy hiểm",
    "lấn làn khi vượt",
    
    # Ngược chiều
    "đi ngược chiều",
    "đi vào đường ngược chiều",
    
    # Tải trọng
    "chở quá tải",
    "xe máy chở 3 người",
    
    # Hàng hóa
    "chở hàng quá khổ",
    "chở hàng không đúng quy định",
    
    # Rượu bia
    "uống rượu bia lái xe",
    "nồng độ cồn vượt quá",
    
    # Tai nạn
    "gây tai nạn giao thông",
    "bỏ chạy sau khi gây tai nạn",
]

def test_question(question: str, url: str = "http://127.0.0.1:8100/chat") -> Dict:
    """Test a single question"""
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
            
            if "[" in full_response and "]" in full_response:
                parts = full_response.rsplit("[", 1)
                if len(parts) == 2:
                    answer = parts[0].strip()
                else:
                    answer = full_response
            else:
                answer = full_response
            
            # Classify response
            is_guardrail = "Xin lỗi, mình chỉ hỗ trợ" in answer
            is_small_talk = "Mình là trợ lý pháp luật giao thông" in answer
            has_legal_info = "Điều" in answer or "khoản" in answer or "phạt" in answer.lower()
            is_error = "Xin lỗi, hiện chưa có thông tin" in answer
            
            status = "success"
            if is_guardrail:
                status = "blocked"
            elif is_small_talk:
                status = "small_talk"
            elif is_error:
                status = "no_info"
            elif not has_legal_info:
                status = "no_legal_info"
            
            return {
                "question": question,
                "status": status,
                "answer": answer[:200],
                "time": elapsed,
                "has_legal_info": has_legal_info,
                "is_guardrail": is_guardrail,
                "is_small_talk": is_small_talk,
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
            "error": str(e)[:100],
            "time": 0
        }

def wait_for_backend(url: str, max_wait: int = 60):
    """Wait for backend to be ready"""
    print("Waiting for backend...")
    for i in range(max_wait // 2):
        try:
            response = requests.get(url.replace("/chat", "/"), timeout=2)
            if response.status_code == 200:
                print("Backend is ready!\n")
                return True
        except:
            pass
        time.sleep(2)
        if i < (max_wait // 2) - 1:
            print(f"  Waiting... ({i*2+2}s)")
    print("ERROR: Backend not responding\n")
    return False

def run_test_cycle(questions: List[str], url: str, cycle_num: int):
    """Run one test cycle"""
    print(f"\n{'='*80}")
    print(f"TEST CYCLE #{cycle_num} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    results = []
    stats = {
        "success": 0,
        "blocked": 0,
        "small_talk": 0,
        "no_info": 0,
        "no_legal_info": 0,
        "error": 0,
    }
    
    for i, question in enumerate(questions, 1):
        print(f"[{i:2d}/{len(questions)}] {question[:50]:<50}", end=" ", flush=True)
        result = test_question(question, url)
        results.append(result)
        
        status = result.get("status", "unknown")
        stats[status] = stats.get(status, 0) + 1
        
        if status == "success":
            print("✓")
        elif status == "blocked":
            print("✗ BLOCKED")
        elif status == "small_talk":
            print("✗ SMALL TALK")
        elif status == "no_info":
            print("⚠ NO INFO")
        elif status == "no_legal_info":
            print("? NO LEGAL INFO")
        else:
            print(f"✗ {status.upper()}")
        
        time.sleep(0.1)  # Small delay
    
    # Summary
    total = len(questions)
    success_rate = (stats["success"] / total * 100) if total > 0 else 0
    
    print(f"\n{'='*80}")
    print("CYCLE SUMMARY")
    print(f"{'='*80}")
    print(f"Total: {total}")
    print(f"✓ Success: {stats['success']} ({stats['success']/total*100:.1f}%)")
    print(f"✗ Blocked: {stats['blocked']} ({stats['blocked']/total*100:.1f}%)")
    print(f"✗ Small Talk: {stats['small_talk']} ({stats['small_talk']/total*100:.1f}%)")
    print(f"⚠ No Info: {stats['no_info']} ({stats['no_info']/total*100:.1f}%)")
    print(f"? No Legal Info: {stats['no_legal_info']} ({stats['no_legal_info']/total*100:.1f}%)")
    print(f"✗ Errors: {stats['error']} ({stats['error']/total*100:.1f}%)")
    print(f"Success Rate: {success_rate:.1f}%")
    
    return results, stats

def main():
    url = "http://127.0.0.1:8100/chat"
    
    print("="*80)
    print("CONTINUOUS TESTING SCRIPT")
    print("="*80)
    print(f"Backend URL: {url}")
    print(f"Total questions: {len(ALL_QUESTIONS)}")
    print(f"Press Ctrl+C to stop\n")
    
    # Wait for backend
    if not wait_for_backend(url):
        return
    
    cycle = 1
    all_results = []
    all_stats = []
    
    try:
        while True:
            results, stats = run_test_cycle(ALL_QUESTIONS, url, cycle)
            all_results.append(results)
            all_stats.append(stats)
            
            # Save results
            output_file = f"test_results_cycle_{cycle}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "cycle": cycle,
                    "timestamp": datetime.now().isoformat(),
                    "results": results,
                    "stats": stats
                }, f, ensure_ascii=False, indent=2)
            
            print(f"\nResults saved to: {output_file}")
            print(f"\nWaiting 30 seconds before next cycle...")
            print("Press Ctrl+C to stop\n")
            
            time.sleep(30)
            cycle += 1
            
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("TESTING STOPPED BY USER")
        print("="*80)
        
        # Final summary
        if all_stats:
            print("\nFINAL SUMMARY (All Cycles):")
            print("-"*80)
            total_cycles = len(all_stats)
            avg_success = sum(s.get("success", 0) for s in all_stats) / total_cycles
            avg_blocked = sum(s.get("blocked", 0) for s in all_stats) / total_cycles
            avg_small_talk = sum(s.get("small_talk", 0) for s in all_stats) / total_cycles
            
            print(f"Total cycles: {total_cycles}")
            print(f"Average success per cycle: {avg_success:.1f}")
            print(f"Average blocked per cycle: {avg_blocked:.1f}")
            print(f"Average small talk per cycle: {avg_small_talk:.1f}")

if __name__ == "__main__":
    main()

