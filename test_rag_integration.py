#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test RAG integration với JSON file"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Test import
print("=" * 60)
print("TEST 1: Import RAG Pipeline")
print("=" * 60)
try:
    from rag_pipeline_with_points import TrafficLawRAGWithPoints
    print("[OK] RAG pipeline imported successfully")
except ImportError as e:
    print(f"❌ Failed to import RAG pipeline: {e}")
    sys.exit(1)

# Test JSON file path
print("\n" + "=" * 60)
print("TEST 2: JSON File Path")
print("=" * 60)
json_path = os.path.join(os.path.dirname(__file__), 'nd168_metadata_clean.json')
print(f"JSON path: {json_path}")
print(f"Exists: {os.path.exists(json_path)}")

if not os.path.exists(json_path):
    print("[ERROR] JSON file not found!")
    sys.exit(1)

# Test RAG initialization
print("\n" + "=" * 60)
print("TEST 3: RAG Initialization")
print("=" * 60)
try:
    rag = TrafficLawRAGWithPoints(json_path)
    print("[OK] RAG initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize RAG: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test retrieval
print("\n" + "=" * 60)
print("TEST 4: RAG Retrieval")
print("=" * 60)
test_questions = [
    "Vượt đèn đỏ bị phạt bao nhiêu?",
    "Không đội mũ bảo hiểm phạt như thế nào?"
]

for q in test_questions:
    print(f"\n📝 Question: {q}")
    try:
        result = rag.retrieve(q)
        if result.get("status") == "success":
            primary = result.get("primary_chunk", {})
            print(f"[OK] Retrieved: {primary.get('reference', 'N/A')}")
            if primary.get("penalty"):
                print(f"   Penalty: {primary['penalty'].get('text', 'N/A')}")
        else:
            print(f"[ERROR] Failed: {result.get('message', 'Unknown')}")
    except Exception as e:
            print(f"[ERROR] Error: {e}")

# Test integration với inference.py
print("\n" + "=" * 60)
print("TEST 5: Integration với inference.py")
print("=" * 60)
try:
    from backend.inference import get_rag_context, RAG_DATA_PATH
    print(f"[OK] RAG_DATA_PATH: {RAG_DATA_PATH}")
    print(f"   Exists: {os.path.exists(RAG_DATA_PATH)}")
    
    # Test get_rag_context
    context = get_rag_context("Vượt đèn đỏ bị phạt bao nhiêu?")
    if context:
        print(f"[OK] get_rag_context works: {len(context)} chars")
        print(f"   Preview: {context[:150]}...")
    else:
        print("[WARNING] No context retrieved")
except Exception as e:
    print(f"[ERROR] Integration test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("[OK] All tests completed!")
print("=" * 60)

