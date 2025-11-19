#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test RAG directly with proper encoding"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from rag_pipeline_with_points import TrafficLawRAGWithPoints

# Test với câu hỏi đúng encoding
question = "Vượt đèn đỏ bị phạt bao nhiêu?"

print("="*60)
print("Testing RAG with question:", question)
print("="*60)

rag = TrafficLawRAGWithPoints('nd168_metadata_clean.json')
result = rag.retrieve(question)

print("\n" + "="*60)
print("RAG Result:")
print(f"Status: {result.get('status')}")
print(f"Message: {result.get('message', 'N/A')}")

if result.get('status') == 'success':
    primary = result.get('primary_chunk', {})
    print(f"\nPrimary Chunk:")
    print(f"  Reference: {primary.get('reference', 'N/A')}")
    print(f"  Penalty: {primary.get('penalty', {}).get('text', 'N/A')}")
    print(f"  Point Deduction: {primary.get('point_deduction', 'N/A')}")
    print(f"  Content: {primary.get('content', 'N/A')[:200]}...")
else:
    print("\nRAG FAILED!")
    print("This means tags were not detected.")

print("="*60)

