# -*- coding: utf-8 -*-
"""
Batch regression for 100 giao thông scenarios.
"""
from backend.inference_hybrid import HybridTrafficLawAssistant


def build_questions() -> list[str]:
    questions: list[str] = []

    # Đèn tín hiệu
    questions += [
        "Ô tô vượt đèn đỏ ở ngã tư bị phạt bao nhiêu?",
        "Xe máy đi thẳng khi đèn đỏ có bị tước GPLX không?",
        "Người đi môtô rẽ trái khi đèn đỏ bị xử lý thế nào?",
        "Ô tô không dừng lại trước đèn vàng nhấp nháy thì phạt sao?",
        "Xe tải không tuân thủ tín hiệu đèn giao thông bị phạt mức nào?",
        "Đi xe máy vượt đèn đỏ gây tai nạn bị phạt thế nào?"
    ]

    # Dây an toàn và trẻ em
    questions += [
        "Tài xế ô tô không thắt dây an toàn bị phạt bao nhiêu?",
        "Người ngồi hàng ghế sau ô tô không cài dây an toàn bị xử lý thế nào?",
        "Chở trẻ em trên ô tô mà không dùng ghế an toàn bị phạt bao nhiêu?",
        "Người ngồi ghế trước không thắt dây an toàn bị tước điểm không?",
        "Khách đi taxi không thắt dây an toàn bị phạt thế nào?"
    ]

    # Điện thoại, thiết bị cầm tay
    questions += [
        "Đang lái ô tô mà cầm điện thoại gọi điện thì bị phạt bao nhiêu?",
        "Xe tải dùng điện thoại khi đang chạy trên cao tốc bị xử lý thế nào?",
        "Điều khiển xe taxi mà bấm điện thoại nhắn tin bị phạt ra sao?",
        "Người lái xe khách mở laptop làm việc khi đang chạy thì phạt bao nhiêu?",
        "Lái ô tô sử dụng thiết bị điện tử cầm tay bị trừ bao nhiêu điểm?"
    ]

    # Nồng độ cồn
    questions += [
        "Lái ô tô có nồng độ cồn 0.03 mg/l khí thở bị phạt thế nào?",
        "Ô tô đo được 0.05 mg/lít khí thở thì bị tước GPLX bao lâu?",
        "Người lái xe máy có nồng độ cồn 70 mg/100ml máu bị xử phạt ra sao?",
        "Lái xe mô tô có cồn vượt quá 80 mg/100ml máu bị phạt thế nào?",
        "Tài xế không chấp hành kiểm tra nồng độ cồn bị xử phạt bao nhiêu?",
        "Người chạy xe máy uống bia nhưng chưa bị đo nồng độ cồn thì có bị phạt không?"
    ]

    # Tốc độ ô tô
    questions += [
        "Ô tô chạy quá tốc độ 12 km/h trong khu dân cư bị phạt bao nhiêu?",
        "Đi xe ô tô vượt quá tốc độ 20 km/h thì bị xử lý thế nào?",
        "Ô tô chạy quá tốc độ 32 km/h có bị tước điểm không?",
        "Xe khách chạy nhanh hơn quy định 40 km/h bị phạt mức nào?",
        "Ô tô chạy quá tốc độ 10 km/h trên cao tốc bị phạt ra sao?"
    ]

    # Tốc độ mô tô
    questions += [
        "Xe máy chạy quá tốc độ 8 km/h thì bị phạt bao nhiêu?",
        "Đi xe máy vượt quá tốc độ 18 km/h bị xử lý thế nào?",
        "Người điều khiển mô tô chạy nhanh hơn 25 km/h bị phạt ra sao?",
        "Xe máy vượt tốc độ 35 km/h gây tai nạn bị phạt thế nào?",
        "Chạy xe máy trong khu dân cư vượt quá tốc độ quy định bị phạt bao nhiêu?"
    ]

    # Đường cấm / ngược chiều / làn đường
    questions += [
        "Xe máy đi vào đường cấm xe máy bị phạt bao nhiêu?",
        "Ô tô đi ngược chiều trên đường một chiều bị xử phạt thế nào?",
        "Xe tải đi vào khu vực hạn chế theo giờ thì bị phạt ra sao?",
        "Lái xe ô tô chuyển làn không có tín hiệu bị phạt bao nhiêu?",
        "Đi xe máy lấn làn gây tai nạn bị xử lý thế nào?",
        "Ô tô đi vào đường cao tốc không đúng loại xe bị phạt mức nào?",
        "Xe khách dừng trên làn khẩn cấp cao tốc để đón khách bị phạt ra sao?",
        "Ô tô quay đầu tại nơi có biển cấm quay đầu bị xử lý thế nào?"
    ]

    # Dừng đỗ sai, bấm còi, mở cửa
    questions += [
        "Ô tô dừng xe nơi có biển cấm dừng bị phạt bao nhiêu?",
        "Đỗ xe trên vạch dành cho người đi bộ thì bị xử lý thế nào?",
        "Đỗ xe trên cầu vượt bị phạt ra sao?",
        "Mở cửa ô tô gây nguy hiểm cho người khác bị phạt bao nhiêu?",
        "Bấm còi rú ga trong khu đông dân cư bị phạt như thế nào?"
    ]

    # Mũ bảo hiểm
    questions += [
        "Người đi xe máy không đội mũ bảo hiểm bị phạt bao nhiêu?",
        "Chở trẻ em 5 tuổi mà không đội mũ bảo hiểm bị xử phạt thế nào?",
        "Đội mũ bảo hiểm nhưng không cài quai có bị phạt không?",
        "Người ngồi sau xe máy đội mũ bảo hiểm nhưng cầm trên tay bị phạt thế nào?",
        "Đi xe máy đèo hai người nhưng chỉ có một mũ bị xử lý ra sao?"
    ]

    # Chở quá tải, quá khổ, hàng nguy hiểm
    questions += [
        "Xe tải chở hàng vượt trọng tải 30% bị phạt bao nhiêu?",
        "Chở hàng vượt trọng tải 50% trên xe container bị xử lý thế nào?",
        "Ô tô tải chở hàng vượt chiều cao cho phép bị phạt ra sao?",
        "Xe tải chở hàng nguy hiểm nhưng không có giấy phép bị phạt thế nào?",
        "Xe khách chở quá 5 người so với quy định thì bị xử phạt ra sao?",
        "Ô tô khách chạy tuyến cố định chở quá 8 người bị phạt bao nhiêu?",
        "Xe tải tụt bạt làm rơi vãi hàng hóa xuống đường thì phạt thế nào?",
        "Xe chở hàng siêu trường không có giấy phép bị xử lý ra sao?"
    ]

    # Giấy tờ, bằng lái, đăng ký
    questions += [
        "Lái xe ô tô không mang theo giấy phép lái xe bị phạt bao nhiêu?",
        "Đi xe máy không mang đăng ký xe bị xử phạt thế nào?",
        "Người lái xe ô tô không có bằng lái bị phạt ra sao?",
        "Điều khiển xe máy bằng giấy phép lái xe hết hạn bị phạt mức nào?",
        "Tài xế xuất trình giấy phép lái xe giả bị xử lý thế nào?",
        "Xe máy không gắn biển số bị phạt bao nhiêu?",
        "Đi xe máy biển số bị che mờ bị xử phạt ra sao?"
    ]

    # Đèn, tín hiệu, xi nhan
    questions += [
        "Ô tô chuyển hướng không bật xi nhan bị phạt bao nhiêu?",
        "Xe máy không bật đèn chiếu sáng ban đêm bị xử lý thế nào?",
        "Ô tô chạy ban ngày nhưng bật đèn pha gây chói mắt bị phạt ra sao?",
        "Xe máy không có gương chiếu hậu bên trái bị phạt bao nhiêu?",
        "Ô tô không có đủ đèn tín hiệu theo quy định thì bị phạt thế nào?"
    ]

    # Vi phạm ở đường sắt, giao cắt
    questions += [
        "Xe máy vượt rào chắn đường sắt bị phạt bao nhiêu?",
        "Ô tô đi vòng tại đường giao nhau có biển nhường đường bị xử lý thế nào?",
        "Xe tải không nhường đường cho người đi bộ tại vạch sang đường bị phạt ra sao?",
        "Ô tô không giảm tốc khi đến gần giao lộ bị phạt bao nhiêu?"
    ]

    # Rượu bia mô tô thêm
    questions += [
        "Đi xe máy mà trong hơi thở có cồn 0.25 mg/l bị xử phạt thế nào?",
        "Người điều khiển mô tô có nồng độ cồn vượt 0.4 mg/l bị phạt ra sao?"
    ]

    # Ô tô doanh nghiệp, kinh doanh
    questions += [
        "Xe taxi đi sai đồng hồ tính tiền bị phạt thế nào?",
        "Xe khách không có hợp đồng vận tải bị xử lý ra sao?",
        "Xe tải kinh doanh không lắp thiết bị giám sát hành trình bị phạt bao nhiêu?",
        "Doanh nghiệp vận tải để lái xe không ký hợp đồng lao động bị phạt thế nào?"
    ]

    # Lỗi khác
    questions += [
        "Xe máy bốc đầu trên đường phố bị phạt bao nhiêu?",
        "Điều khiển xe máy lạng lách đánh võng bị xử lý thế nào?",
        "Ô tô kéo theo xe khác bằng dây không đúng quy định bị phạt ra sao?",
        "Xe máy kéo theo người bằng ván trượt bị phạt bao nhiêu?",
        "Xe máy đi thành đoàn ba chiếc song song bị phạt thế nào?",
        "Ô tô nẹt pô gây ồn ào trong đêm bị xử phạt ra sao?",
        "Xe máy chạy bằng một bánh bị phạt bao nhiêu?",
        "Ô tô sử dụng đèn ưu tiên trái phép bị xử lý thế nào?",
        "Xe máy chở hàng cồng kềnh vượt quá bề rộng cho phép bị phạt bao nhiêu?",
        "Ô tô chạy vào làn xe buýt nhanh BRT bị xử lý thế nào?",
        "Xe mô tô đi vào hầm đường bộ nhưng không bật đèn bị phạt bao nhiêu?",
        "Ô tô phun khói đen vượt tiêu chuẩn môi trường bị phạt ra sao?",
        "Xe máy không nhường đường cho xe cứu hỏa đang làm nhiệm vụ bị phạt thế nào?",
        "Ô tô quay đầu trong hầm vượt bị xử lý ra sao?",
        "Xe tải không phủ bạt để bụi rơi vãi bị phạt bao nhiêu?",
        "Người đi xe đạp điện không đội mũ bảo hiểm bị phạt thế nào?",
        "Xe máy đi vào đường cao tốc bị xử lý ra sao?",
        "Ô tô không lắp camera hành trình theo quy định kinh doanh bị phạt bao nhiêu?",
        "Đi xe máy kéo theo xe khác bằng dây bị phạt thế nào?",
        "Ô tô đậu xe chắn cửa nhà người khác bị xử lý ra sao?"
    ]

    # Bổ sung để đủ 100
    questions += [
        "Xe khách đón trả khách không đúng nơi quy định bị phạt bao nhiêu?",
        "Ô tô vận chuyển hàng nguy hiểm không có biển cảnh báo bị xử lý thế nào?",
        "Xe máy đi qua phà không tuân theo hướng dẫn bị phạt ra sao?",
        "Ô tô chạy vào làn thu phí không dừng nhưng không đủ tiền bị xử lý thế nào?",
        "Xe máy đỗ trên cầu vượt dành cho người đi bộ bị phạt bao nhiêu?",
        "Người điều khiển mô tô kéo theo xe khác gây tai nạn bị xử lý ra sao?",
        "Ô tô sử dụng biển số giả bị phạt mức nào?",
        "Xe taxi đón khách trên cao tốc bị xử phạt thế nào?",
        "Ô tô đi vào đường hầm mà quay đầu bị phạt ra sao?",
        "Xe tải chở gỗ vượt chiều dài cho phép bị phạt bao nhiêu?",
        "Xe khách để cửa mở khi chạy bị xử lý thế nào?",
        "Ô tô không có bình chữa cháy theo quy định bị phạt ra sao?",
        "Xe mô tô đi vào vùng hạn chế tiếng ồn vào ban đêm bị phạt thế nào?",
        "Ô tô dừng đỗ trên phần đường xe điện chạy bị phạt bao nhiêu?",
        "Xe máy chở hàng dài quá 3 mét bị xử lý ra sao?",
        "Ô tô chạy sang đường sắt khi chắn đang đóng bị phạt thế nào?",
        "Xe tải chạy vào đường cấm giờ cao điểm bị phạt bao nhiêu?",
        "Ô tô chạy sai làn đường dành cho xe thô sơ bị xử lý thế nào?",
        "Xe máy đi sát hành lang an toàn giao thông đường sắt bị phạt ra sao?",
        "Ô tô không gắn thiết bị thu phí tự động theo quy định bị phạt bao nhiêu?"
    ]

    if len(questions) > 100:
        questions = questions[:100]

    assert len(questions) == 100, f"Expected 100 questions, got {len(questions)}"
    return questions


def run_regression():
    assistant = HybridTrafficLawAssistant(use_generation=False)
    assistant.question_rewriter_enabled = False

    failures: list[tuple[int, str, dict]] = []
    successes = 0

    for idx, question in enumerate(build_questions(), start=1):
        result = assistant.answer(question)
        status = result.get("status")
        source = result.get("source")
        answer = result.get("answer")
        reference = result.get("reference")

        print(f"[{idx:03d}] {question}")
        print(f"     status={status} source={source} reference={reference}")
        print(f"     answer={answer}")
        print("-" * 100)

        if status == "success" and answer:
            successes += 1
        else:
            failures.append((idx, question, result))

    total = idx
    print("=" * 100)
    print(f"Tổng câu hỏi: {total}")
    print(f"Thành công: {successes}")
    print(f"Thất bại: {len(failures)}")
    if failures:
        print("Danh sách câu thất bại:")
        for idx, question, result in failures:
            print(f"  #{idx:03d} {question} -> status={result.get('status')} message={result.get('message')}")


if __name__ == "__main__":
    run_regression()

