# Chỉ Ra Cụ Thể Các Phần Trong Code

## BƯỚC 1: Normalize & Guardrail Check

### 1.1. Normalize Input
**File**: `backend/inference_hybrid.py`
- **Dòng 919**: `normalized_question = normalize_input_text(question)`
- **Function**: `normalize_input_text()` được import từ `backend.inference` (dòng 140-143)

### 1.2. Guardrail Classification
**File**: `backend/inference_hybrid.py`
- **Dòng 920**: `guardrail_mode = self._guardrail_classify(normalized_question)`
- **Method `_guardrail_classify()`**: **Dòng 786-830**
  - **Dòng 793-804**: Check small talk patterns (`SMALL_TALK_PATTERNS`)
  - **Dòng 806-808**: Check out-of-scope patterns (`OUT_OF_SCOPE_PATTERNS`)
  - **Dòng 810-828**: Heuristic check - câu hỏi ngắn không có từ khóa pháp lý

### 1.3. Guardrail Response
**File**: `backend/inference_hybrid.py`
- **Dòng 921-922**: Nếu phát hiện guardrail → return ngay
- **Method `_guardrail_response()`**: **Dòng 832-851**
  - **Dòng 833-842**: Response cho small talk
  - **Dòng 843-851**: Response cho out-of-scope

### 1.4. Constants
**File**: `backend/inference_hybrid.py`
- **Dòng 31-34**: `DEFAULT_SMALL_TALK_REPLY`
- **Dòng 35-38**: `DEFAULT_OUT_OF_SCOPE_REPLY`
- **Dòng 39-55**: `SMALL_TALK_PATTERNS`
- **Dòng 56-68**: `OUT_OF_SCOPE_PATTERNS`
- **Dòng 69-138**: `LEGAL_KEYWORDS`

---

## BƯỚC 2: Question Rewriting (Optional)

**File**: `backend/inference_hybrid.py`
- **Dòng 924-926**: Gọi `_rewrite_question()` và cập nhật nếu có kết quả
- **Method `_rewrite_question()`**: **Dòng 481-605**
  - **Dòng 483-484**: Check nếu rewriting enabled
  - **Dòng 486-488**: Detect Gemini API
  - **Dòng 490-511**: Build payload cho Gemini
  - **Dòng 512-515**: Build payload cho custom API
  - **Dòng 536-541**: Gửi request đến API
  - **Dòng 545-590**: Parse response từ nhiều format khác nhau
  - **Dòng 586-590**: Normalize và return nếu khác câu hỏi gốc

### Configuration
**File**: `backend/inference_hybrid.py`
- **Dòng 216-225**: Load config từ environment variables
  - `QUESTION_REWRITER_URL`
  - `QUESTION_REWRITER_TOKEN`
  - `QUESTION_REWRITER_MODEL`
  - `QUESTION_REWRITER_TIMEOUT`

---

## BƯỚC 3: RAG Retrieval

**File**: `rag_pipeline_with_points.py`

### 3.1. Entry Point
**File**: `backend/inference_hybrid.py`
- **Dòng 933**: `retrieval_result = self._retrieve_with_variations(normalized_question)`
- **Method `_retrieve_with_variations()`**: **Dòng 347-352** trong `inference_hybrid.py`
  - Gọi `self.rag.retrieve(question)` (RAG pipeline)

### 3.2. Extract Tags
**File**: `rag_pipeline_with_points.py`
- **Dòng 779**: `query_tags = self._extract_tags(query)`
- **Method `_extract_tags()`**: **Dòng 361-376**
  - **Dòng 363-370**: Loop qua `BEHAVIOR_KEYWORDS` để tìm tags
- **Constants**: **Dòng 29-250**: `BEHAVIOR_KEYWORDS` dictionary

### 3.3. Detect Context
**File**: `rag_pipeline_with_points.py`
- **Dòng 781**: `has_tai_nan = any(keyword in query_lower for keyword in ESCALATION_INDICATORS["gay_tai_nan"])`
- **Dòng 791**: `is_organization = any(keyword in query_lower for keyword in [...])`
- **Dòng 794**: `vehicle_article = self._detect_vehicle_type(query)`
  - **Method `_detect_vehicle_type()`**: **Dòng 421-449**
- **Dòng 795**: `speed_kmh = self._extract_speed_range(query)`
  - **Method `_extract_speed_range()`**: **Dòng 451-466**
- **Dòng 798-807**: Detect engine size (cho xe máy)

### 3.4. Semantic Search
**File**: `rag_pipeline_with_points.py`
- **Dòng 842-853**: Check và gọi semantic search
- **Method `_semantic_search()`**: **Dòng 1433-1475**
  - **Dòng 1440-1444**: Encode query thành embedding
  - **Dòng 1457**: Tính similarity scores
  - **Dòng 1461-1463**: Lấy top-k indices
  - **Dòng 1465-1474**: Filter theo min_score và return

### 3.5. Filter by Subject Type
**File**: `rag_pipeline_with_points.py`
- **Dòng 871-886**: Filter cá nhân vs tổ chức
  - **Dòng 872-880**: Cá nhân → Điều 6-21
  - **Dòng 881-886**: Tổ chức → Điều 30+

### 3.6. Filter by Vehicle Type
**File**: `rag_pipeline_with_points.py`
- **Dòng 888-910**: Filter theo vehicle article
  - **Dòng 901-905**: Chỉ lấy chunks match vehicle_article
  - **Dòng 890-899**: Skip filter cho một số trường hợp đặc biệt (đua xe, tải trọng)

### 3.7. Content-Based Filtering
**File**: `rag_pipeline_with_points.py`
- **Dòng 912-1004**: Nhiều lớp filter theo content
  - **Dòng 921-930**: Filter xe mô tô theo text
  - **Dòng 931-940**: Filter xe ô tô theo text
  - **Dòng 943-956**: Filter tải trọng
  - **Dòng 959-967**: Filter ngược chiều
  - **Dòng 970-979**: Filter đường cấm
  - **Dòng 982-991**: Filter đèn tín hiệu
  - **Dòng 994-1003**: Filter điện thoại

### 3.8. Tag-Specific Keyword Rules
**File**: `rag_pipeline_with_points.py`
- **Dòng 1009**: `behavior_chunks = self._filter_by_keyword_rules(behavior_chunks, query_tags)`
- **Method `_filter_by_keyword_rules()`**: **Dòng 378-419**
  - **Dòng 388-391**: Loop qua tags và lấy rules
  - **Dòng 393-401**: Tính positive/negative scores
  - **Dòng 405-417**: Filter chunks theo best score

### 3.9. Speed Violation Handling
**File**: `rag_pipeline_with_points.py`
- **Dòng 828-835**: Xác định target khoản cho speed violation
- **Method `_get_speed_violation_khoan()`**: **Dòng 468-504**
  - **Dòng 484-494**: Logic cho xe ô tô (Điều 6)
  - **Dòng 496-502**: Logic cho xe mô tô (Điều 7)
- **Dòng 1012-1020**: Filter chunks theo target khoản

### 3.10. Match Base Behaviors + Escalations
**File**: `rag_pipeline_with_points.py`
- **Dòng 1022-1024**: Collect behavior references
- **Dòng 1029-1033**: Add base behavior chunks (non-escalation)
- **Dòng 1036-1053**: Add escalation chunks
  - **Dòng 1040-1041**: Filter theo vehicle article
  - **Dòng 1044-1045**: Filter theo target khoản (nếu có)
  - **Dòng 1047-1049**: Check ref_match, tag_match, tai_nan_match

### 3.11. Select Primary Chunk
**File**: `rag_pipeline_with_points.py`
- **Dòng 1055-1301**: Logic chọn primary chunk (RẤT PHỨC TẠP)
  - **Dòng 1062-1080**: Filter chunks có penalty info
  - **Dòng 1066-1080**: Exact phrase matching
  - **Dòng 1082-1101**: Context-based location filtering (hầm vs đường)
  - **Dòng 1104-1120**: Exact matches (không có tai nạn)
  - **Dòng 1122-1183**: Tai nạn handling
    - **Dòng 1125-1131**: Khoản 13 special case
    - **Dòng 1136-1178**: Escalation chunks priority
  - **Dòng 1184-1297**: Normal violations
    - **Dòng 1189-1229**: Specific tag filtering
    - **Dòng 1231-1257**: Special case "không mang" vs "không có"
    - **Dòng 1259-1264**: Engine size filtering
    - **Dòng 1266-1276**: Business transport (van_tai) filtering
    - **Dòng 1279-1297**: Final selection logic

### 3.12. Extract Related Chunks
**File**: `rag_pipeline_with_points.py`
- **Dòng 1320-1324**: Collect related candidates
- **Dòng 1324**: Sort theo penalty (reverse)

### 3.13. Format Response
**File**: `rag_pipeline_with_points.py`
- **Dòng 1326-1360**: Build return dictionary
  - **Dòng 1328-1337**: Primary chunk với đầy đủ thông tin
  - **Dòng 1339-1358**: Related chunks (tối đa 3)

---

## BƯỚC 4: Context Formatting

**File**: `backend/inference_hybrid.py`
- **Dòng 936**: `context = self._format_context(retrieval_result) if retrieval_success else ""`
- **Method `_format_context()`**: **Dòng 369-401**
  - **Dòng 370-371**: Check status
  - **Dòng 372**: Validate chunk
  - **Dòng 376-401**: Build formatted text
    - **Dòng 376**: Header
    - **Dòng 377-388**: Primary chunk info
    - **Dòng 390-399**: Related chunks

### Validate Chunk
**File**: `backend/inference_hybrid.py`
- **Method `_validate_chunk()`**: **Dòng 354-367**
  - **Dòng 360-361**: Truncate content > 300 chars
  - **Dòng 365-366**: Truncate penalty text > 150 chars

---

## BƯỚC 5: LLM Generation

**File**: `backend/inference_hybrid.py`

### 5.1. Check Generation Enabled
- **Dòng 941**: `if self.use_generation:`
- **Dòng 945-950**: Gọi `_generate_with_model()`

### 5.2. Build Prompt
**File**: `backend/inference_hybrid.py`
- **Method `_build_prompt()`**: **Dòng 608-625**
  - **Dòng 609-614**: System message
  - **Dòng 616-624**: User prompt với context

### 5.3. Generate
**File**: `backend/inference_hybrid.py`
- **Method `_generate_with_model()`**: **Dòng 681-739**
  - **Dòng 689-693**: Check model/tokenizer available
  - **Dòng 692-693**: Build prompt
  - **Dòng 694-696**: Tokenize input
  - **Dòng 697-698**: Move to device
  - **Dòng 700**: Normalize max tokens
  - **Dòng 701-712**: Model generation với parameters
  - **Dòng 714**: Decode output
  - **Dòng 715-720**: Extract answer từ chat template
  - **Dòng 722**: Clean answer
  - **Dòng 724-732**: Filter small talk responses
  - **Dòng 734-739**: Return cleaned answer hoặc empty

### 5.4. Clean Answer
**File**: `backend/inference_hybrid.py`
- **Method `_clean_answer()`**: **Dòng 627-679**
  - **Dòng 633**: Remove date patterns
  - **Dòng 634-641**: Remove Chinese patterns
  - **Dòng 643-652**: Remove English filler words
  - **Dòng 655-675**: Filter sentences có quá nhiều từ tiếng Anh
  - **Dòng 677-678**: Collapse whitespace

### 5.5. Model Loading
**File**: `backend/inference_hybrid.py`
- **Method `_load_model()`**: **Dòng 263-344**
  - **Dòng 265**: Check unsloth available
  - **Dòng 267-298**: Load với unsloth (nếu có)
  - **Dòng 304-344**: Fallback to transformers
  - **Dòng 329-344**: Backup model nếu primary fail

---

## BƯỚC 6: Answer Validation & Source Selection

**File**: `backend/inference_hybrid.py`
- **Method `answer()`**: **Dòng 918-1075**

### 6.1. Filter Small Talk After Generation
- **Dòng 953-970**: Check nếu model answer là small talk
  - **Dòng 956-963**: Small talk patterns
  - **Dòng 964**: Check match
  - **Dòng 965-970**: Clear answer nếu là small talk

### 6.2. Answer Selection Logic
- **Dòng 972-1005**: Logic chọn answer
  - **Dòng 973-982**: Force model output (nếu enabled)
  - **Dòng 983-994**: RAG failed nhưng có raw model answer
    - **Dòng 985-991**: Filter small talk
  - **Dòng 995-1005**: RAG succeeded → dùng fallback

### 6.3. Final Small Talk Check
- **Dòng 1009-1040**: Check lại small talk trong final answer
  - **Dòng 1012-1022**: Small talk indicators
  - **Dòng 1024-1027**: Check match
  - **Dòng 1029-1040**: Replace với fallback nếu là small talk

### 6.4. Append RAG Citation
- **Dòng 1042-1065**: Append citation nếu cần
  - **Dòng 1044-1051**: Check xem model answer đã có reference và penalty chưa
  - **Dòng 1054-1062**: Append citation nếu chưa đủ
  - **Method `_build_rag_citation_only()`**: **Dòng 450-478**

### 6.5. Build Fallback Answer
**File**: `backend/inference_hybrid.py`
- **Method `_build_fallback_answer()`**: **Dòng 403-448**
  - **Dòng 405-406**: Check status
  - **Dòng 409-441**: Build segments từ primary chunk
  - **Dòng 445-448**: Join và cleanup

---

## BƯỚC 7: Final Response

**File**: `backend/inference_hybrid.py`
- **Dòng 1067-1075**: Return final response dictionary
  - **Dòng 1068**: Status
  - **Dòng 1069**: Normalized question
  - **Dòng 1070**: Final answer
  - **Dòng 1071**: Context
  - **Dòng 1072**: Reference
  - **Dòng 1073**: Source (model/fallback/etc.)
  - **Dòng 1074**: Raw model answer

---

## Các Helper Methods Quan Trọng

### Strip Diacritics
**File**: `backend/inference_hybrid.py`
- **Method `strip_diacritics()`**: **Dòng 151-156**
- Dùng cho fallback search queries

### Normalize Max Tokens
**File**: `backend/inference_hybrid.py`
- **Method `_normalize_max_tokens()`**: **Dòng 252-261**
- Clamp requested tokens vào safe range

### Answer Without RAG
**File**: `backend/inference_hybrid.py`
- **Method `_answer_without_rag()`**: **Dòng 853-915**
- Generate trực tiếp từ model không có RAG context

### Generate From Prompt
**File**: `backend/inference_hybrid.py`
- **Method `generate_from_prompt()`**: **Dòng 741-783**
- Expose raw prompt generation cho remote generator service

---

## RAG Pipeline Helper Methods

### Extract Point Deduction
**File**: `rag_pipeline_with_points.py`
- **Method `_extract_point_deduction()`**: **Dòng 579-626`
- Tính điểm trừ dựa trên article, khoản, điểm

### Extract License Suspension
**File**: `rag_pipeline_with_points.py`
- **Method `_extract_license_suspension()`**: **Dòng 628-667`
- Tính thời gian tước GPLX

### Extract Penalty Amounts
**File**: `rag_pipeline_with_points.py`
- **Method `_extract_penalty_amounts()`**: **Dòng 550-577`
- Parse mức phạt từ text

### Format Penalty
**File**: `rag_pipeline_with_points.py`
- **Method `_format_penalty()`**: **Dòng 1477-1493`
- Format số tiền phạt theo định dạng Việt Nam

### Setup Semantic Search
**File**: `rag_pipeline_with_points.py`
- **Method `_setup_semantic_search()`**: **Dòng 1363-1412`
- Load semantic index từ disk

### Get Semantic Encoder
**File**: `rag_pipeline_with_points.py`
- **Method `_get_semantic_encoder()`**: **Dòng 1414-1431`
- Lazy load SentenceTransformer encoder

---

## Constants & Configuration

### RAG Pipeline Constants
**File**: `rag_pipeline_with_points.py`
- **Dòng 24**: `SEMANTIC_DEFAULT_MODEL`
- **Dòng 25-26**: `CROSS_VEHICLE_TAGS`, `CROSS_VEHICLE_ARTICLES`
- **Dòng 29-250**: `BEHAVIOR_KEYWORDS` (rất lớn)
- **Dòng 253-267**: `ESCALATION_INDICATORS`
- **Dòng 269-309**: `TAG_CONTENT_RULES`

### Hybrid Assistant Constants
**File**: `backend/inference_hybrid.py`
- **Dòng 146**: `DEFAULT_HF_TOKEN`
- **Dòng 147**: `DEFAULT_HF_REPO`
- **Dòng 148**: `DEFAULT_HF_SUBFOLDER`
- **Dòng 159-165**: `SYNONYM_MAP`

---

## Initialization

### HybridTrafficLawAssistant.__init__
**File**: `backend/inference_hybrid.py`
- **Dòng 171-250**: Constructor
  - **Dòng 177-180**: Load data path
  - **Dòng 181-200**: Determine model path (local vs hub)
  - **Dòng 202-213**: Generation config
  - **Dòng 216-244**: Question rewriter config
  - **Dòng 246**: Initialize RAG
  - **Dòng 247-250**: Load model (nếu use_generation)

### TrafficLawRAGWithPoints.__init__
**File**: `rag_pipeline_with_points.py`
- **Dòng 334-359**: Constructor
  - **Dòng 335**: Data path
  - **Dòng 336-340**: Initialize indices
  - **Dòng 343-356**: Semantic search config
  - **Dòng 358**: Load and process data
  - **Dòng 359**: Setup semantic search

---

## API Integration

### FastAPI Endpoint
**File**: `backend/app.py`
- **Dòng 80-132**: `/chat` endpoint
  - **Dòng 86-92**: Normalize question
  - **Dòng 97-105**: Call `assistant.answer()`
  - **Dòng 118-122**: Small talk delay (3 seconds)
  - **Dòng 129-130**: Stream answer word by word

### Get Hybrid Assistant
**File**: `backend/app.py`
- **Dòng 31-36**: Lazy initialization
- **Dòng 39-55**: Startup event - preload assistant

