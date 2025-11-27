from code_mau_infer.rag_nd168_ttatgtdb import TrafficLawRAG2Laws

rag = TrafficLawRAG2Laws()
result = rag.retrieve("dừng xe là gì?", verbose=True)
print(result)
