#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test RAG retrieval"""

import sys
sys.path.insert(0, '.')

from rag_pipeline_with_points import TrafficLawRAGWithPoints

rag = TrafficLawRAGWithPoints('nd168_metadata_clean.json')

questions = [
    "Vượt đèn đỏ bị phạt bao nhiêu?",
    "Không đội mũ bảo hiểm phạt như thế nào?"
]

for q in questions:
    print(f"\n{'='*60}")
    print(f"Question: {q}")
    print('='*60)
    result = rag.retrieve(q)
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        p = result.get('primary_chunk', {})
        print(f"Reference: {p.get('reference', 'N/A')}")
        if p.get('penalty'):
            print(f"Penalty: {p.get('penalty', {}).get('text', 'N/A')}")
        if p.get('point_deduction'):
            print(f"Point Deduction: {p.get('point_deduction')}")
    else:
        print(f"Error: {result.get('message', 'Unknown')}")

