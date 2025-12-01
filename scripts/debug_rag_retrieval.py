#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug RAG retrieval for small talk questions
"""
import sys
sys.path.insert(0, '.')

from rag_pipeline_with_points import TrafficLawRAGWithPoints

QUESTIONS = [
    "sử dụng điện thoại khi lái xe",
    "nghe điện thoại khi đang điều khiển xe máy",
    "không bật đèn khi đi ban đêm",
    "không bật xi-nhan khi rẽ",
    "lấn làn khi vượt",
    "bỏ chạy sau khi gây tai nạn",
]

def main():
    rag = TrafficLawRAGWithPoints("nd168_metadata_clean.json")
    
    print("="*80)
    print("Debugging RAG Retrieval for Small Talk Questions")
    print("="*80)
    
    for question in QUESTIONS:
        print(f"\n{'='*80}")
        print(f"Question: {question}")
        print(f"{'='*80}")
        
        result = rag.retrieve(question)
        
        print(f"Status: {result.get('status')}")
        print(f"Message: {result.get('message', 'N/A')}")
        
        if result.get('status') == 'success':
            primary = result.get('primary_chunk', {})
            print(f"Primary chunk found:")
            print(f"  Reference: {primary.get('reference', 'N/A')}")
            print(f"  Content: {primary.get('content', 'N/A')[:100]}...")
            print(f"  Penalty: {primary.get('penalty', {}).get('text', 'N/A')[:100]}...")
        else:
            print("No chunks found!")
            print(f"Reason: {result.get('message', 'Unknown')}")

if __name__ == "__main__":
    main()

