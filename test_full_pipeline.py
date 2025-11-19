#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test full pipeline: RAG + Model generation"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.inference import get_rag_context, get_answer
import json

def test_rag_retrieval():
    """Test RAG context retrieval"""
    print("=" * 60)
    print("TEST 1: RAG Context Retrieval")
    print("=" * 60)
    
    test_questions = [
        "Vượt đèn đỏ bị phạt bao nhiêu?",
        "Không đội mũ bảo hiểm phạt như thế nào?",
        "Nếu xe máy không đội mũ vượt đèn đỏ thì sao?",
        "Chạy quá tốc độ trừ bao nhiêu điểm?"
    ]
    
    for q in test_questions:
        print(f"\nQuestion: {q}")
        context = get_rag_context(q)
        if context:
            print(f"RAG Context retrieved: {len(context)} chars")
            print(f"Preview: {context[:200]}...")
        else:
            print("No RAG context retrieved")
    
    print("\n" + "=" * 60)

def test_model_generation():
    """Test model generation with RAG"""
    print("\n" + "=" * 60)
    print("TEST 2: Model Generation with RAG")
    print("=" * 60)
    
    test_questions = [
        "Vượt đèn đỏ bị phạt bao nhiêu?",
        "Không đội mũ bảo hiểm phạt như thế nào?"
    ]
    
    for q in test_questions:
        print(f"\nQuestion: {q}")
        print("-" * 60)
        try:
            answer = get_answer(q)
            print(f"Answer ({len(answer)} chars):")
            print(answer[:300] + "..." if len(answer) > 300 else answer)
            
            # Check for issues
            issues = []
            if "2025-" in answer or "2024-" in answer:
                issues.append("Contains timestamp")
            if any(ord(c) > 0x7F and 0x4E00 <= ord(c) <= 0x9FFF for c in answer):
                issues.append("Contains Chinese characters")
            if len(answer) > 500:
                issues.append("Answer too long")
            if answer.count(' ') < 5:
                issues.append("Answer too short")
            
            if issues:
                print("\nIssues found:")
                for issue in issues:
                    print(f"  {issue}")
            else:
                print("\nNo issues detected")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)

def test_output_cleaning():
    """Test output cleaning"""
    print("\n" + "=" * 60)
    print("TEST 3: Output Cleaning")
    print("=" * 60)
    
    test_outputs = [
        "Theo quy định 2025-01-01 18:30:47 +08:00",
        "Trả lời bằng tiếng Việt 如果您有其他问题",
        "Câu trả lời ngắn gọn 2024-12-31",
        "Thông tin pháp luật ### Response"
    ]
    
    import re
    for output in test_outputs:
        print(f"\nOriginal: {output}")
        cleaned = output
        # Remove timestamp patterns
        cleaned = re.sub(r'\d{4}-\d{2}-\d{2}[\s:]*\d{2}:\d{2}:\d{2}.*', '', cleaned)
        cleaned = re.sub(r'\d{4}-\d{2}-\d{2}.*', '', cleaned)
        # Remove Chinese characters
        cleaned = re.sub(r'[^\x00-\x7F\u00C0-\u1EF9\s.,!?;:()\[\]{}\-]+', '', cleaned)
        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        print(f"Cleaned:  {cleaned}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    print("\nTesting Full Pipeline\n")
    
    # Test 1: RAG retrieval
    test_rag_retrieval()
    
    # Test 2: Output cleaning
    test_output_cleaning()
    
    # Test 3: Model generation (only if model is loaded)
    print("\nModel generation test requires model to be loaded.")
    print("   Run this after backend is started.\n")
    
    # Uncomment to test model generation:
    # test_model_generation()

