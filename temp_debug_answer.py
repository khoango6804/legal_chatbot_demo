from backend.inference_hybrid import HybridTrafficLawAssistant

assistant = HybridTrafficLawAssistant(use_generation=False)
result = assistant.answer("dừng xe là gì?")
print(result)
