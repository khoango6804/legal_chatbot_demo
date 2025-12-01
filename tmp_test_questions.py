from backend.inference_hybrid import HybridTrafficLawAssistant

questions = [
    "Xe máy vượt đèn đỏ thì bị phạt như thế nào?",
    "Ô tô vượt đèn đỏ phạt bao nhiêu?",
    "Đi xe máy không đội mũ bảo hiểm bị phạt thế nào?",
    "Không thắt dây an toàn khi lái ô tô bị phạt bao nhiêu?",
    "Người ngồi sau ô tô không thắt dây đai an toàn thì sao?",
    "Lái xe ô tô sau khi uống rượu với nồng độ cồn 0.05 mg/l khí thở bị phạt thế nào?",
    "Điều khiển xe máy đi vào đường ngược chiều bị xử lý ra sao?",
    "Ô tô đâm người đi bộ gây thương tích thì bị xử lý thế nào?",
    "Xe máy chạy quá tốc độ 25 km/h bị phạt bao nhiêu?",
    "Xe ô tô chạy quá tốc độ 20 km/h bị xử phạt thế nào?",
    "Không mang theo giấy phép lái xe máy bị phạt bao nhiêu?",
    "Không có giấy phép lái xe ô tô thì bị phạt như thế nào?",
    "Xe máy chở ba người thì bị xử lý ra sao?",
    "Xe máy đi vào đường cấm bị phạt bao nhiêu?",
    "Ô tô sử dụng điện thoại khi đang lái bị phạt thế nào?",
    "Xe tải chở hàng vượt quá tải trọng 50% bị phạt bao nhiêu?",
    "Điều khiển xe máy lạng lách đánh võng bị phạt bao nhiêu?",
    "Xe máy không bật đèn khi chạy ban đêm bị xử lý ra sao?",
    "Ô tô không nhường đường cho xe cứu thương bị phạt thế nào?",
    "Người điều khiển xe máy gây tai nạn rồi bỏ chạy bị xử lý ra sao?"
]

assistant = HybridTrafficLawAssistant(use_generation=False)
assistant.question_rewriter_enabled = False

for q in questions:
    result = assistant.answer(q)
    print("QUESTION:", q)
    print("STATUS:", result.get("status"), "SOURCE:", result.get("source"))
    print("ANSWER:", result.get("answer"))
    print("REFERENCE:", result.get("reference"))
    print("-" * 80)
