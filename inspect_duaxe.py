from rag_pipeline_with_points import TrafficLawRAGWithPoints

rag = TrafficLawRAGWithPoints('nd168_metadata_clean.json')
query = 'xe máy đua xe bị phạt gì?'
result = rag.retrieve(query)
print('status', result.get('status'))
print('message', result.get('message'))
primary = result.get('primary_chunk') or {}
print('primary reference', primary.get('reference'))
print('primary content', primary.get('content'))
print('penalty min/max', primary.get('penalty'))
print('point deduction', primary.get('point_deduction'))
print('license suspension', primary.get('license_suspension'))
