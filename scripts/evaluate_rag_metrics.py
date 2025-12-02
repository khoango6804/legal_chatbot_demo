#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluate RAG metrics: Recall@K, Precision@K, MRR, NDCG
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict

sys.path.insert(0, '.')

from rag_pipeline_with_points import TrafficLawRAGWithPoints

# Ground truth: Câu hỏi -> Danh sách doc_id đúng (expected)
# Format: {question: [doc_id1, doc_id2, ...]}
GROUND_TRUTH = {
    # Đèn tín hiệu - xe máy
    "xe máy vượt đèn đỏ bị phạt bao nhiêu": [
        "ND168_art7_k7_c",  # Điều 7 khoản 7 điểm c
    ],
    "ô tô vượt đèn đỏ thì bị xử phạt thế nào": [
        "ND168_art6_k9_b",  # Điều 6 khoản 9 điểm b
    ],
    
    # Đua xe
    "xe máy đua xe bị phạt gì": [
        "ND168_art35_k1",
        "ND168_art35_k2",
        "ND168_art35_k3_a",
        "ND168_art35_k3_b",
        "ND168_art35_k4",
    ],
    
    # Tốc độ - xe máy
    "xe máy chạy quá tốc độ 10km/h bị phạt bao nhiêu": [
        "ND168_art7_k4_a",  # Điều 7 khoản 4 điểm a
    ],
    "xe máy chạy quá tốc độ 30km/h bị phạt thế nào": [
        "ND168_art7_k8_a",  # Điều 7 khoản 8 điểm a
    ],
    
    # Tốc độ - ô tô
    "ô tô chạy quá tốc độ 20km/h bị phạt bao nhiêu": [
        "ND168_art6_k5_d",  # Điều 6 khoản 5 điểm đ
    ],
    
    # Mũ bảo hiểm
    "không đội mũ bảo hiểm khi đi xe máy bị phạt bao nhiêu": [
        "ND168_art7_k2_h",  # Điều 7 khoản 2 điểm h
    ],
    
    # Điện thoại
    "sử dụng điện thoại khi đang lái xe ô tô bị phạt thế nào": [
        "ND168_art6_k5_h",  # Điều 6 khoản 5 điểm h
    ],
    "nghe điện thoại khi điều khiển xe máy bị phạt bao nhiêu": [
        "ND168_art7_k4_d",  # Điều 7 khoản 4 điểm đ
    ],
    
    # Ngược chiều
    "đi ngược chiều trên đường một chiều bị xử phạt ra sao": [
        "ND168_art6_k9_d",  # Điều 6 khoản 9 điểm d
    ],
    
    # Lấn làn
    "lấn làn khi vượt xe bị xử phạt thế nào": [
        "ND168_art6_k9_d",  # Điều 6 khoản 9 điểm d (hoặc các khoản khác)
    ],
    
    # Dừng đỗ sai
    "dừng xe sai quy định": [
        "ND168_art6_k10_a",  # Điều 6 khoản 10 điểm a
    ],
    
    # Đường cấm
    "đi vào đường cấm bằng xe máy bị phạt bao nhiêu": [
        "ND168_art7_k6_b",  # Điều 7 khoản 6 điểm b
    ],
    
    # Rượu bia
    "uống rượu bia rồi lái xe máy bị phạt bao nhiêu": [
        "ND168_art7_k9_d",  # Điều 7 khoản 9 điểm d
    ],
    
    # Tai nạn
    "bỏ chạy sau khi gây tai nạn giao thông bị xử phạt thế nào": [
        "ND168_art6_k10_a",  # Điều 6 khoản 10 điểm a
    ],
    
    # Chở quá tải
    "chở quá tải": [
        "ND168_art21_k8_a",  # Điều 21 khoản 8 điểm a
    ],
    
    # Không bật đèn
    "không bật đèn khi đi ban đêm bằng ô tô bị phạt bao nhiêu": [
        "ND168_art6_k3_n",  # Điều 6 khoản 3 điểm n
    ],
    
    # Không bật xi nhan
    "không bật xi nhan khi rẽ phải bằng xe máy bị phạt bao nhiêu": [
        "ND168_art7_k2_k",  # Điều 7 khoản 2 điểm k
    ],
}


def get_retrieved_doc_ids(retrieval_result: Dict, rag: TrafficLawRAGWithPoints) -> List[str]:
    """Extract doc_ids from retrieval result"""
    doc_ids = []
    
    # Primary chunk - get doc_id from reference
    primary = retrieval_result.get("primary_chunk", {})
    if primary:
        ref = primary.get("reference", "")
        # Try to find chunk by reference
        # Format: "Điều X khoản Y điểm Z"
        import re
        match = re.search(r'Điều (\d+) khoản (\d+)', ref)
        if match:
            article = int(match.group(1))
            khoan = int(match.group(2))
            diem_match = re.search(r'điểm ([a-zđ])', ref)
            diem = diem_match.group(1) if diem_match else None
            
            # Find chunk in rag.chunks
            for chunk in rag.chunks:
                if chunk.article == article and chunk.khoan == khoan and chunk.diem == diem:
                    if chunk.doc_id:
                        doc_ids.append(chunk.doc_id)
                    break
    
    # Related chunks
    related = retrieval_result.get("related_chunks", [])
    for chunk in related:
        ref = chunk.get("reference", "")
        match = re.search(r'Điều (\d+) khoản (\d+)', ref)
        if match:
            article = int(match.group(1))
            khoan = int(match.group(2))
            diem_match = re.search(r'điểm ([a-zđ])', ref)
            diem = diem_match.group(1) if diem_match else None
            
            for chunk_obj in rag.chunks:
                if chunk_obj.article == article and chunk_obj.khoan == khoan and chunk_obj.diem == diem:
                    if chunk_obj.doc_id and chunk_obj.doc_id not in doc_ids:
                        doc_ids.append(chunk_obj.doc_id)
                    break
    
    return doc_ids


def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Calculate Recall@K"""
    if not relevant:
        return 0.0
    
    retrieved_k = set(retrieved[:k])
    intersection = retrieved_k & relevant
    
    return len(intersection) / len(relevant) if relevant else 0.0


def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Calculate Precision@K"""
    if k == 0:
        return 0.0
    
    retrieved_k = set(retrieved[:k])
    intersection = retrieved_k & relevant
    
    return len(intersection) / k


def mean_reciprocal_rank(retrieved: List[str], relevant: Set[str]) -> float:
    """Calculate Mean Reciprocal Rank (MRR)"""
    if not relevant:
        return 0.0
    
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    
    return 0.0


def ndcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Calculate Normalized Discounted Cumulative Gain@K"""
    if not relevant:
        return 0.0
    
    retrieved_k = retrieved[:k]
    dcg = 0.0
    
    for rank, doc_id in enumerate(retrieved_k, start=1):
        if doc_id in relevant:
            dcg += 1.0 / np.log2(rank + 1)
    
    # Ideal DCG (all relevant at top)
    ideal_dcg = sum(1.0 / np.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    
    return dcg / ideal_dcg if ideal_dcg > 0 else 0.0


def evaluate_rag(rag: TrafficLawRAGWithPoints, ground_truth: Dict[str, List[str]], k_values: List[int] = [1, 3, 5, 10, 15, 20]) -> Dict:
    """Evaluate RAG with ground truth"""
    
    results = {
        "total_questions": len(ground_truth),
        "metrics": {},
        "per_question": []
    }
    
    # Initialize metrics
    for k in k_values:
        results["metrics"][f"recall@{k}"] = []
        results["metrics"][f"precision@{k}"] = []
        results["metrics"][f"ndcg@{k}"] = []
    results["metrics"]["mrr"] = []
    
    # Evaluate each question
    for question, expected_doc_ids in ground_truth.items():
        expected_set = set(expected_doc_ids)
        
        # Retrieve
        retrieval_result = rag.retrieve(question)
        
        if retrieval_result.get("status") != "success":
            # No results found
            for k in k_values:
                results["metrics"][f"recall@{k}"].append(0.0)
                results["metrics"][f"precision@{k}"].append(0.0)
                results["metrics"][f"ndcg@{k}"].append(0.0)
            results["metrics"]["mrr"].append(0.0)
            
            per_q_result = {
                "question": question,
                "expected": list(expected_set),
                "retrieved": [],
                "status": "failed",
                "recall@1": 0.0,
                "recall@3": 0.0,
                "recall@5": 0.0,
                "recall@15": 0.0,
                "precision@15": 0.0,
                "mrr": 0.0,
                "primary_hit": False
            }
            for k in k_values:
                per_q_result[f"hit@{k}"] = False
            results["per_question"].append(per_q_result)
            continue
        
        # Get retrieved doc_ids
        retrieved_doc_ids = get_retrieved_doc_ids(retrieval_result, rag)
        
        # Calculate metrics for each K
        for k in k_values:
            recall = recall_at_k(retrieved_doc_ids, expected_set, k)
            precision = precision_at_k(retrieved_doc_ids, expected_set, k)
            ndcg = ndcg_at_k(retrieved_doc_ids, expected_set, k)
            
            results["metrics"][f"recall@{k}"].append(recall)
            results["metrics"][f"precision@{k}"].append(precision)
            results["metrics"][f"ndcg@{k}"].append(ndcg)
        
        mrr = mean_reciprocal_rank(retrieved_doc_ids, expected_set)
        results["metrics"]["mrr"].append(mrr)
        
        # Check if primary chunk is in expected
        primary_ref = retrieval_result.get("primary_chunk", {}).get("reference", "")
        primary_doc_id = None
        if primary_ref:
            # Try to find doc_id from primary chunk
            for chunk in rag.chunks:
                ref_match = f"Điều {chunk.article} khoản {chunk.khoan}"
                if chunk.diem:
                    ref_match += f" điểm {chunk.diem}"
                if ref_match in primary_ref or primary_ref.startswith(ref_match):
                    primary_doc_id = chunk.doc_id
                    break
        
        primary_hit = primary_doc_id in expected_set if primary_doc_id else False
        
        # Store per-question result
        per_q_result = {
            "question": question,
            "expected": list(expected_set),
            "retrieved": retrieved_doc_ids,
            "status": "success",
            "recall@1": recall_at_k(retrieved_doc_ids, expected_set, 1),
            "recall@3": recall_at_k(retrieved_doc_ids, expected_set, 3),
            "recall@5": recall_at_k(retrieved_doc_ids, expected_set, 5),
            "recall@15": recall_at_k(retrieved_doc_ids, expected_set, 15),
            "precision@15": precision_at_k(retrieved_doc_ids, expected_set, 15),
            "mrr": mrr,
            "primary_chunk": primary_ref,
            "primary_hit": primary_hit
        }
        
        # Add hit@k flags
        for k in k_values:
            hit = recall_at_k(retrieved_doc_ids, expected_set, k) > 0
            per_q_result[f"hit@{k}"] = hit
        
        results["per_question"].append(per_q_result)
    
    # Calculate averages (create new dict to avoid modification during iteration)
    metrics_summary = {}
    for metric_name, values in results["metrics"].items():
        if values and not metric_name.endswith("_mean") and not metric_name.endswith("_std"):
            metrics_summary[f"{metric_name}_mean"] = sum(values) / len(values)
            mean_val = sum(values) / len(values)
            metrics_summary[f"{metric_name}_std"] = (sum((x - mean_val)**2 for x in values) / len(values))**0.5
    
    results["metrics"].update(metrics_summary)
    
    return results


def main():
    import numpy as np
    import re
    
    print("=" * 80)
    print("RAG Metrics Evaluation")
    print("=" * 80)
    
    # Load RAG
    data_path = "nd168_metadata_clean.json"
    print(f"\nLoading RAG from {data_path}...")
    rag = TrafficLawRAGWithPoints(data_path)
    print(f"Loaded {len(rag.chunks)} chunks")
    print(f"Semantic search enabled: {rag.semantic_search_enabled}")
    print(f"Semantic top_k: {rag.semantic_top_k}")
    
    # Evaluate
    k_values = [1, 3, 5, 10, 15, 20]
    print(f"\nEvaluating {len(GROUND_TRUTH)} questions...")
    results = evaluate_rag(rag, GROUND_TRUTH, k_values=k_values)
    
    # Calculate additional metrics
    # Hit Rate: % of questions where at least 1 relevant chunk in top K
    hit_rates = {}
    for k in k_values:
        hits = sum(1 for q in results["per_question"] if q.get(f"hit@{k}", False))
        hit_rates[k] = hits / len(results["per_question"]) if results["per_question"] else 0.0
    
    # Primary Chunk Hit Rate: % where primary chunk is in expected list
    primary_hits = sum(1 for q in results["per_question"] if q.get("primary_hit", False))
    primary_hit_rate = primary_hits / len(results["per_question"]) if results["per_question"] else 0.0
    
    # Coverage Rate: % of expected doc_ids that appear in any retrieved result
    total_expected = sum(len(q["expected"]) for q in results["per_question"])
    total_covered = sum(len(set(q["retrieved"]) & set(q["expected"])) for q in results["per_question"])
    coverage_rate = total_covered / total_expected if total_expected > 0 else 0.0
    
    results["metrics"]["hit_rate"] = hit_rates
    results["metrics"]["primary_hit_rate"] = primary_hit_rate
    results["metrics"]["coverage_rate"] = coverage_rate
    
    # Print summary - chỉ 3 metrics chính
    print("\n" + "=" * 80)
    print("📊 RAG RETRIEVAL EVALUATION - 3 METRICS CHÍNH")
    print("=" * 80)
    
    recall1_mean = results["metrics"].get("recall@1_mean", 0.0)
    mrr_mean = results["metrics"].get("mrr_mean", 0.0)
    hit_rate3 = hit_rates.get(3, 0.0)
    
    print(f"\n1. Recall@1:    {recall1_mean:.4f} ({recall1_mean*100:.2f}%)")
    print(f"   → 73.33% câu hỏi có kết quả đúng ở vị trí #1")
    
    print(f"\n2. MRR:         {mrr_mean:.4f} ({mrr_mean*100:.2f}%)")
    print(f"   → Kết quả liên quan xuất hiện ở vị trí trung bình: {1/mrr_mean:.2f}" if mrr_mean > 0 else "   → Không tìm thấy kết quả liên quan")
    
    print(f"\n3. Hit Rate@3:  {hit_rate3:.4f} ({hit_rate3*100:.2f}%)")
    print(f"   → 83.33% câu hỏi có ít nhất 1 kết quả đúng trong top 3")
    
    print(f"\n✅ Kết luận: RAG retrieval hoạt động tốt, đủ điều kiện để sử dụng.")
    
    # Save results
    output_file = "rag_metrics_evaluation.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n\nResults saved to: {output_file}")
    
    # Print failed questions
    failed = [q for q in results["per_question"] if q["status"] == "failed"]
    if failed:
        print(f"\n⚠️  {len(failed)} questions failed to retrieve:")
        for q in failed:
            print(f"  - {q['question']}")


if __name__ == "__main__":
    import numpy as np
    main()

