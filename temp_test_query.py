from rag_pipeline_with_points import TrafficLawRAGWithPoints
rag = TrafficLawRAGWithPoints("nd168_metadata_clean.json")
print(rag.retrieve("dừng xe là gì?"))
