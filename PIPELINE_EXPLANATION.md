# Giải Thích Chi Tiết Pipeline Hybrid RAG + LLM

## Tổng Quan

Pipeline này là một hệ thống **Hybrid RAG (Retrieval-Augmented Generation)** kết hợp:
- **RAG (Retrieval)**: Tìm kiếm thông tin từ cơ sở dữ liệu luật giao thông
- **LLM (Generation)**: Sử dụng mô hình ngôn ngữ để tạo câu trả lời tự nhiên
- **Fallback**: Có cơ chế dự phòng khi RAG hoặc LLM thất bại

---

## Luồng Xử Lý Tổng Thể

```
Câu hỏi người dùng
    ↓
1. Normalize & Guardrail Check
    ↓
2. Question Rewriting (Optional)
    ↓
3. RAG Retrieval
    ↓
4. Context Formatting
    ↓
5. LLM Generation (Optional)
    ↓
6. Answer Validation & Cleaning
    ↓
7. Fallback nếu cần
    ↓
Câu trả lời cuối cùng
```

---

## Chi Tiết Từng Bước

### BƯỚC 1: Normalize & Guardrail Check

**File**: `backend/inference_hybrid.py` - Method `answer()` (dòng 918-922)

**Mục đích**: Chuẩn hóa câu hỏi và lọc các câu hỏi không liên quan

**Quy trình**:
1. **Normalize input**: 
   - Chuẩn hóa encoding (UTF-8)
   - Loại bỏ ký tự đặc biệt
   - Xử lý Unicode

2. **Guardrail Classification** (`_guardrail_classify`):
   - **Small talk**: "bạn là ai", "xin chào", "hello" → Trả về câu trả lời mặc định
   - **Out of scope**: "bóng đá", "thời tiết", "crypto" → Trả về thông báo ngoài phạm vi
   - **Kiểm tra từ khóa pháp lý**: Nếu câu hỏi ngắn (<5 từ) và không có từ khóa giao thông → out of scope

**Ví dụ**:
```python
# Input: "xin chào"
# → Phát hiện small talk
# → Trả về: "Mình là trợ lý pháp luật giao thông..."
```

---

### BƯỚC 2: Question Rewriting (Optional)

**File**: `backend/inference_hybrid.py` - Method `_rewrite_question()` (dòng 481-605)

**Mục đích**: Viết lại câu hỏi cho rõ ràng, đầy đủ hơn

**Điều kiện kích hoạt**:
- Có cấu hình `QUESTION_REWRITER_URL` trong environment
- Hỗ trợ Gemini API hoặc custom API

**Quy trình**:
1. Gửi câu hỏi gốc đến API rewriter
2. Nhận câu hỏi đã viết lại
3. Normalize lại câu hỏi mới
4. Sử dụng câu hỏi mới cho RAG

**Ví dụ**:
```python
# Input: "phạt bao nhiêu?"
# → Rewritten: "Mức phạt tiền cho vi phạm này là bao nhiêu?"
```

---

### BƯỚC 3: RAG Retrieval

**File**: `rag_pipeline_with_points.py` - Method `retrieve()` (dòng 776-1360)

Đây là bước **phức tạp nhất** với nhiều lớp lọc và logic:

#### 3.1. Extract Tags từ Câu Hỏi

**Method**: `_extract_tags()` (dòng 361-376)

- Phân tích câu hỏi để tìm các **behavior tags** (nhãn hành vi)
- Ví dụ tags: `den_tin_hieu`, `re_phai`, `qua_toc_do`, `khong_doi_mu`, etc.
- Mỗi tag có danh sách từ khóa tương ứng trong `BEHAVIOR_KEYWORDS`

**Ví dụ**:
```python
# Câu hỏi: "Vượt đèn đỏ bị phạt bao nhiêu?"
# → Tags: {"den_tin_hieu"}
```

#### 3.2. Detect Context (Vehicle Type, Speed, etc.)

**Methods**:
- `_detect_vehicle_type()`: Xe ô tô (Điều 6) hay xe mô tô (Điều 7)
- `_extract_speed_range()`: Tốc độ vi phạm (nếu có)
- Detect subject: Cá nhân hay tổ chức
- Detect tai nạn: Có gây tai nạn không

**Ví dụ**:
```python
# "Xe máy chạy quá tốc độ 25km/h"
# → Vehicle: Điều 7 (mô tô)
# → Speed: 25 km/h
# → Target khoản: 8 (vì >20km/h)
```

#### 3.3. Semantic Search (Optional)

**Method**: `_semantic_search()` (dòng 1433-1475)

- Nếu có semantic index (embeddings.npy), thực hiện tìm kiếm ngữ nghĩa
- Sử dụng SentenceTransformer để encode câu hỏi
- Tìm top-k chunks có similarity score cao nhất
- Bổ sung vào danh sách candidates từ keyword search

#### 3.4. Filter by Subject Type

**Logic** (dòng 871-886):
- **Cá nhân**: Chỉ lấy Điều 6-21 (vi phạm cá nhân)
- **Tổ chức**: Chỉ lấy Điều 30+ (vi phạm doanh nghiệp)

#### 3.5. Filter by Vehicle Type

**Logic** (dòng 888-910):
- Nếu phát hiện "xe ô tô" → chỉ lấy Điều 6
- Nếu phát hiện "xe mô tô" → chỉ lấy Điều 7
- Tránh nhầm lẫn giữa quy định ô tô và mô tô

#### 3.6. Content-Based Filtering

**Logic** (dòng 912-1004):
- Lọc theo từ khóa trong nội dung chunk
- Ví dụ: Nếu query về "đèn tín hiệu", ưu tiên chunks có chứa "đèn tín hiệu" trong text
- Áp dụng cho: đèn tín hiệu, điện thoại, tải trọng, ngược chiều, đường cấm

#### 3.7. Tag-Specific Keyword Rules

**Method**: `_filter_by_keyword_rules()` (dòng 378-419)

- Một số tags có quy tắc đặc biệt:
  - **Positive keywords**: Phải có trong chunk
  - **Negative keywords**: Không được có trong chunk
- Ví dụ: `den_tin_hieu` cần có "vượt đèn" nhưng không được có "dừng xe"

#### 3.8. Speed Violation Special Handling

**Method**: `_get_speed_violation_khoan()` (dòng 468-504)

- Nếu phát hiện vi phạm tốc độ, xác định khoản chính xác:
  - **Xe ô tô**: 5-10km/h → khoản 4, 10-20km/h → khoản 5, 20-35km/h → khoản 6, >35km/h → khoản 7
  - **Xe mô tô**: 10-20km/h → khoản 4, >20km/h → khoản 8
  - Có tai nạn → khoản 10 (escalation)

#### 3.9. Match Base Behaviors + Escalations

**Logic** (dòng 1026-1053):
- **Base behaviors**: Chunks không phải escalation, match với tags
- **Escalations**: Chunks mô tả quy định nâng mức phạt
  - Escalation match nếu:
    - References của nó match với base behaviors đã tìm được
    - Tags của nó match với query tags
    - Có tai nạn và priority = 100

#### 3.10. Select Primary Chunk

**Logic** (dòng 1055-1301) - **Rất phức tạp**:

**Ưu tiên theo thứ tự**:

1. **Exact phrase matches** (không có tai nạn):
   - Nếu có chunks match chính xác cụm từ trong query
   - Ưu tiên chunks theo vehicle type (ô tô → Điều 13, mô tô → Điều 14)
   - Chọn chunk có penalty thấp nhất (base violation)

2. **Tai nạn với khoản 13**:
   - Nếu có khoản 12 (lạng lách) và khoản 13 (lạng lách + tai nạn)
   - Ưu tiên khoản 13 (escalation)

3. **Tai nạn thông thường**:
   - Ưu tiên escalation chunks (is_escalation=True)
   - Trong escalations, ưu tiên khoản 10
   - Sort theo priority (100 > 90 > 80) rồi penalty

4. **Normal violations**:
   - Filter theo specific tags (co_vu_dua_xe > khong_mang_bang_lai > khong_bang_lai > ...)
   - Filter theo vehicle type trong text
   - Filter theo engine size (nếu có)
   - Filter theo business transport (van_tai)
   - Chọn chunk có penalty cao nhất (trừ một số trường hợp đặc biệt)

5. **Fallback**: Chọn chunk đầu tiên trong matched_chunks

#### 3.11. Extract Related Chunks

- Lấy các chunks khác (không phải primary) đã match
- Sort theo penalty (cao → thấp)
- Giới hạn 3 chunks

#### 3.12. Format Response

**Return structure**:
```python
{
    "status": "success",
    "primary_chunk": {
        "reference": "Điều 6 khoản 4 điểm i",
        "content": "...",
        "penalty": {"min": 800000, "max": 1000000, "text": "800.000đ - 1.000.000đ"},
        "point_deduction": 2,
        "license_suspension": {"min_months": 1, "max_months": 3, "text": "..."}
    },
    "related_chunks": [...]
}
```

---

### BƯỚC 4: Context Formatting

**File**: `backend/inference_hybrid.py` - Method `_format_context()` (dòng 369-401)

**Mục đích**: Chuyển đổi kết quả RAG thành context text cho LLM

**Format**:
```
=== THÔNG TIN LUẬT CHÍNH ===
Điều khoản: Điều 6 khoản 4 điểm i
Nội dung: [content]
Mức phạt: [penalty text]
Trừ điểm: [points] điểm
Tước GPLX: [suspension text]
Thông tin bổ sung:
- [related chunk 1]
- [related chunk 2]
```

**Validation**: 
- Giới hạn content ≤ 300 ký tự
- Giới hạn penalty text ≤ 150 ký tự

---

### BƯỚC 5: LLM Generation (Optional)

**File**: `backend/inference_hybrid.py` - Method `_generate_with_model()` (dòng 681-739)

**Điều kiện**: 
- `use_generation = True`
- Model đã được load

#### 5.1. Build Prompt

**Method**: `_build_prompt()` (dòng 608-625)

**Format** (Qwen chat template):
```
<|im_start|>system
Bạn là trợ lý pháp luật giao thông Việt Nam. Trả lời CHÍNH XÁC theo dữ liệu cung cấp.
Quy tắc:
- Luôn nêu đủ mức phạt tiền + trừ điểm + tước GPLX (nếu có).
- Sao chép đúng số tiền, số tháng, số điểm.
- Không thêm thông tin ngoài dữ liệu.
- Trả lời 2-3 câu, tiếng Việt chuẩn.<|im_end|>
<|im_start|>user
Câu hỏi: [question]

[context from RAG]
<|im_end|>
<|im_start|>assistant
Theo [reference]:
```

#### 5.2. Generate

**Parameters**:
- `max_new_tokens`: 120 (default) hoặc từ request
- `temperature`: 0.6
- `top_p`: 0.95
- `top_k`: 20
- `repetition_penalty`: 1.2

#### 5.3. Extract Answer

- Tách phần sau `<|im_start|>assistant`
- Dừng ở `<|im_end|>`

#### 5.4. Clean Answer

**Method**: `_clean_answer()` (dòng 627-679)

**Quy trình**:
1. Loại bỏ date patterns (YYYY-MM-DD)
2. Loại bỏ Chinese characters
3. Loại bỏ English filler words
4. Loại bỏ sentences có quá nhiều từ tiếng Anh (không có dấu)
5. Collapse whitespace

#### 5.5. Validate Answer

**Checks**:
- Độ dài ≥ 20 ký tự
- Không phải tiếng Anh/Trung (Vietnamese fallback check)
- Không phải small talk response
- Nếu không pass → return empty string (trigger fallback)

---

### BƯỚC 6: Answer Validation & Source Selection

**File**: `backend/inference_hybrid.py` - Method `answer()` (dòng 918-1075)

**Logic quyết định** (dòng 972-1065):

#### 6.1. Nếu có Model Answer (cleaned)

1. **Check small talk filter**:
   - Nếu model trả về small talk → clear answer, dùng fallback

2. **Append RAG citation** (nếu RAG thành công):
   - Kiểm tra xem model answer đã có reference và penalty chưa
   - Nếu chưa đủ → append citation từ RAG
   - Format: `\n\n---\n[Trích dẫn: Điều X khoản Y]\n[Thông tin bổ sung]`

3. **Source**: `"model"` hoặc `"model_with_rag_citation"`

#### 6.2. Nếu không có Model Answer

1. **Force model output** (nếu enabled):
   - Dùng raw model answer (chưa clean)
   - Source: `"model_forced"`

2. **RAG succeeded**:
   - Dùng fallback answer từ RAG
   - Source: `"fallback"`

3. **RAG failed**:
   - Kiểm tra raw model answer có phải small talk không
   - Nếu là small talk → dùng error message
   - Nếu không → dùng raw model answer
   - Source: `"model_no_rag"` hoặc `"fallback_no_rag"`

#### 6.3. Build Fallback Answer

**Method**: `_build_fallback_answer()` (dòng 403-448)

**Format**:
```
Theo [reference], [content]. Mức phạt: [penalty]. Trừ điểm: [points] điểm. Tước GPLX: [suspension].
Thông tin bổ sung: [related chunks]
```

---

### BƯỚC 7: Final Response

**Return structure**:
```python
{
    "status": "success",
    "question": "[normalized question]",
    "answer": "[final answer text]",
    "context": "[formatted context]",
    "reference": "[Điều X khoản Y]",
    "source": "[model|fallback|model_with_rag_citation|...]",
    "model_raw_answer": "[raw model output]"
}
```

---

## Các Tính Năng Đặc Biệt

### 1. Small Talk Detection

**Mục đích**: Tránh model trả lời small talk khi có RAG context

**Implementation**:
- Check trong `_generate_with_model()` (dòng 724-732)
- Check trong `answer()` sau khi generate (dòng 954-970)
- Check trong final answer (dòng 1009-1040)

**Patterns**:
- "mình là trợ lý"
- "luôn sẵn sàng"
- "bạn cứ đặt câu hỏi"

### 2. Question Rewriting

**Use case**: Câu hỏi mơ hồ → viết lại cho rõ ràng

**Example**:
```
Input: "phạt bao nhiêu?"
Rewritten: "Mức phạt tiền cho vi phạm này là bao nhiêu?"
```

### 3. Semantic Search Fallback

**Khi nào**: Khi keyword search không tìm thấy tags

**How**: Sử dụng embeddings để tìm chunks tương tự về ngữ nghĩa

### 4. Escalation Handling

**Ví dụ**: 
- Base: Vượt tốc độ 25km/h → khoản 8 (6-8M)
- Escalation: Vượt tốc độ 25km/h + tai nạn → khoản 10 (20-22M)

**Logic**: 
- Match base behavior trước
- Sau đó tìm escalation chunks có references match
- Ưu tiên escalation nếu có tai nạn

### 5. Vehicle Type Filtering

**Vấn đề**: Tránh nhầm lẫn quy định ô tô và mô tô

**Solution**:
- Detect vehicle type từ query
- Filter chunks theo article (6 hoặc 7)
- Filter theo text content (có mention "xe ô tô" hay "xe mô tô")

### 6. Speed Violation Precision

**Ví dụ**: "Chạy quá tốc độ 25km/h"
- Xe ô tô: 20-35km/h → khoản 6
- Xe mô tô: >20km/h → khoản 8

**Logic**: `_get_speed_violation_khoan()` xác định khoản chính xác dựa trên:
- Vehicle type
- Speed amount
- Có tai nạn không

---

## Error Handling & Fallbacks

### RAG Failed
- Nếu không tìm thấy chunks → return error message
- Nếu có model → thử generate không có context
- Nếu không có model → return error

### Model Generation Failed
- Nếu answer quá ngắn hoặc không phải tiếng Việt → dùng fallback
- Nếu model trả về small talk → dùng fallback
- Nếu force_model_output → dùng raw answer

### Fallback Answer
- Luôn có sẵn từ RAG data
- Format deterministic (không phụ thuộc model)
- Đảm bảo luôn có câu trả lời

---

## Performance Considerations

1. **Lazy Model Loading**: Model chỉ load khi cần
2. **Semantic Index Caching**: Embeddings load một lần
3. **Chunk Filtering**: Nhiều lớp filter để giảm số lượng chunks xử lý
4. **Token Limits**: Giới hạn max_new_tokens để tránh generation quá dài

---

## Configuration

**Environment Variables**:
- `USE_GENERATIVE_MODEL`: Bật/tắt LLM generation
- `FORCE_MODEL_OUTPUT`: Luôn dùng model output (kể cả khi không clean)
- `MAX_NEW_TOKENS`: Số token tối đa generate
- `QUESTION_REWRITER_URL`: URL cho question rewriting API
- `SEMANTIC_INDEX_DIR`: Thư mục chứa semantic index
- `SEMANTIC_TOP_K`: Số chunks lấy từ semantic search
- `SEMANTIC_MIN_SCORE`: Ngưỡng similarity score

---

## Tóm Tắt

Pipeline này là một hệ thống **hybrid** với nhiều lớp bảo vệ:

1. **Guardrails**: Lọc câu hỏi không liên quan
2. **RAG**: Tìm thông tin chính xác từ database
3. **LLM**: Tạo câu trả lời tự nhiên
4. **Validation**: Đảm bảo chất lượng answer
5. **Fallback**: Luôn có câu trả lời dự phòng

Ưu điểm:
- ✅ Độ chính xác cao (RAG-based)
- ✅ Câu trả lời tự nhiên (LLM)
- ✅ Robust (nhiều fallback)
- ✅ Xử lý edge cases tốt

Nhược điểm:
- ⚠️ Phức tạp (nhiều logic)
- ⚠️ Latency cao (RAG + LLM)
- ⚠️ Cần maintain nhiều components

