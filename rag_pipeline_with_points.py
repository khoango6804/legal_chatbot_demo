#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced RAG Pipeline for Traffic Law with License Point Deduction
Extends rag_pipeline_qwen3.py with point deduction tracking
"""

import json
import os
import re
from pathlib import Path
from typing import Any, List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

# Behavior keyword mapping
SEMANTIC_DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CROSS_VEHICLE_TAGS = {"dua_xe", "co_vu_dua_xe"}
CROSS_VEHICLE_ARTICLES = {35}


BEHAVIOR_KEYWORDS = {
    "den_tin_hieu": [
        "vượt đèn",
        "vượt đèn đỏ",
        "không chấp hành hiệu lệnh của đèn",
        "không chấp hành tín hiệu đèn",
        "không dừng đèn đỏ",
        "đèn tín hiệu",
        "đèn giao thông",
        "đèn đỏ",
        "đèn vàng",
        "đi thẳng khi đèn đỏ",
        "tín hiệu đèn giao thông"
    ],
    "re_phai": ["rẽ phải", "rẽ trái", "quay đầu xe", "quay đầu", "chuyển hướng"],
    "can_vach": ["cán vạch", "vạch phân làn", "vạch kẻ đường", "cán lên vạch"],
    "chuyen_lan": ["chuyển làn", "đổi làn", "sang làn"],
    "luot_trai_pha_cam": [
        "lấn làn",
        "đi ngược chiều",
        "vượt ẩu",
        "đi không đúng làn",
        "đường ngược chiều",
        "ngược chiều",
        "đi vào đường ngược chiều"
    ],
    "qua_toc_do": [
        "quá tốc độ",
        "vượt tốc độ",
        "chạy quá tốc độ",
        "chạy nhanh hơn",
        "đi nhanh hơn"
    ],
    "khong_doi_mu": [
        "không đội mũ",
        "mũ bảo hiểm",
        "không đội nón",
        "chỉ có một mũ",
        "thiếu mũ"
    ],
    "dung_do_sai": [
        "dừng xe",
        "đỗ xe",
        "đậu xe sai quy định",
        "làn khẩn cấp",
        "dải dừng khẩn cấp",
        "chắn cửa nhà"
    ],
    "chay_khu_cam": [
        "khu vực cấm",
        "nơi cấm dừng",
        "nơi cấm đỗ",
        "đường cấm",
        "đi vào đường cấm",
        "cấm đường",
        "khu vực hạn chế",
        "làn buýt",
        "brt"
    ],
    "dien_thoai": [
        "điện thoại",
        "nghe điện thoại",
        "dùng điện thoại",
        "sử dụng điện thoại",
        "thiết bị điện tử",
        "laptop",
        "máy tính bảng"
    ],
    "khong_bat_den": ["không bật đèn", "không bật xi-nhan", "không có đèn", "không sử dụng đèn"],
    "den_pha": ["đèn pha", "đèn chiếu xa", "đèn chiếu sáng gây chói"],
    "mo_cua": ["mở cửa xe", "mở cửa ô tô", "để cửa xe mở"],
    "cho_qua_nguoi": [
        "chở quá người",
        "quá số người",
        "vượt quá số lượng",
        "tống 3",
        "tống ba",
        "chở 3",
        "chở ba người",
        "đi 3 người",
        "đi ba người",
        "chở quá số người",
        "vượt quá số người",
        "chở quá"
    ],
    "khong_bang_lai": [
        "không có bằng lái",
        "không giấy phép",
        "chưa có bằng",
        "giấy phép giả",
        "bằng lái hết hạn",
        "giấy phép lái xe giả",
        "giấy phép lái xe hết hạn"
    ],
    "gay_tai_nan": [
        "gây tai nạn",
        "tai nạn giao thông",
        "va chạm gây thương tích",
        "đâm người",
        "đâm phải",
        "tông người",
        "va chạm",
        "đụng người"
    ],
    "uong_ruou_bia": [
        "nồng độ cồn",
        "uống rượu",
        "uống bia",
        "say rượu",
        "có cồn",
        "mg/l",
        "mg/100ml"
    ],
    "lang_lach": ["lạng lách", "đánh võng", "drift", "biểu diễn"],
    "boc_dau": ["bốc đầu", "chạy bằng một bánh", "nâng bánh trước", "wheelie", "chạy một bánh"],
    "khong_nhuong_duong": [
        "không nhường đường",
        "cản trở xe ưu tiên",
        "không giảm tốc",
        "biển nhường đường"
    ],
    "vuot_xe_sai": ["vượt xe", "vượt bên phải", "vượt không đúng"],
    "tram_cam": ["cầm máy", "không tắt máy", "để máy nổ", "còi", "rú ga", "nẹt pô"],
    "cao_toc": [
        "cao tốc",
        "đường cao tốc",
        "làn khẩn cấp",
        "dải khẩn cấp",
        "làn dừng khẩn cấp"
    ],
    "cho_hang": [
        "chở hàng",
        "quá tải",
        "chở quá khổ",
        "vượt quá tải trọng",
        "tải trọng",
        "trọng tải",
        "vượt trọng tải",
        "tụt bạt",
        "rơi vãi",
        "không phủ bạt"
    ],
    "dieu_khien_nguy_hiem": ["buông cả hai tay", "dùng chân điều khiển", "ngồi về một bên", "nằm trên yên", 
                             "thay người điều khiển", "quay người về phía sau", "bịt mắt điều khiển",
                             "buông tay", "không cầm tay lái", "điều khiển bằng chân"],
    "khong_bien_so": [
        "không gắn biển số",
        "biển số xe",
        "biển kiểm soát",
        "không có biển số",
        "gắn biển số không đúng",
        "che biển số",
        "che mờ biển số",
        "che mờ"
    ],
    "thiet_bi": [
        "gương chiếu hậu",
        "camera hành trình",
        "thiết bị giám sát hành trình",
        "bình chữa cháy",
        "thiết bị bắt buộc"
    ],
    "khong_giay_to": [
        "không mang giấy",
        "giấy chứng nhận",
        "chứng nhận đăng ký",
        "không có giấy tờ",
        "đăng ký xe"
    ],
    "day_an_toan": [
        "không thắt dây an toàn",
        "không thắt dây đai",
        "không cài dây an toàn",
        "không cài dây đai",
        "không đeo dây an toàn",
        "không sử dụng dây an toàn",
        "không mang dây an toàn",
        "ghế an toàn",
        "ghế trẻ em",
        "khách không thắt dây"
    ],
    "khong_mang_bang_lai": ["không mang theo giấy phép lái xe", "không mang theo bằng lái", "không mang giấy phép", "không mang bằng lái"],
    "khong_bang_lai": [
        "không có giấy phép lái xe",
        "không có bằng lái",
        "giấy phép giả",
        "bằng lái hết hạn",
        "giấy phép lái xe giả",
        "giấy phép lái xe hết hạn"
    ],
    "keo_xe": [
        "kéo xe",
        "kéo rơ moóc",
        "kéo theo xe khác",
        "kéo theo người",
        "ván trượt"
    ],
    "dan_hang_ngang": [
        "dàn hàng ngang",
        "chạy dàn hàng",
        "đi song song",
        "đi thành đoàn"
    ],
    "chay_trong_ham": ["chạy trong hầm", "hầm đường bộ"],
    "khong_thu_phi": ["không thu phí", "không dừng thu phí", "thu phí điện tử"],
    "duong_sat": ["đường sắt", "rào chắn", "giao cắt đường sắt"],
    "den_uu_tien": [
        "đèn ưu tiên",
        "thiết bị ưu tiên",
        "thiết bị phát tín hiệu ưu tiên"
    ],
    "moi_truong": [
        "khói đen",
        "khí thải vượt chuẩn",
        "khí thải",
        "giảm khói"
    ],
    "van_tai": ["vận tải", "kinh doanh vận tải", "hoạt động vận tải", "đồng hồ tính tiền", "giám sát hành trình", "camera hành trình"],
    "tai_pham": ["tái phạm", "vi phạm lần 2", "vi phạm lại"],
    "dua_xe": ["đua xe", "đua xe trái phép", "chạy đua", "đua tốc độ"],
    "co_vu_dua_xe": ["cổ vũ đua xe", "tụ tập đua xe", "cổ vũ", "tụ tập để cổ vũ", "giúp sức đua xe", "xúi giục đua xe"]
}

# Escalation indicators
ESCALATION_INDICATORS = {
    "gay_tai_nan": [
        "gây tai nạn",
        "làm chết người",
        "gây thương tích",
        "tai nạn giao thông",
        "đâm",
        "tông",
        "va chạm",
        "đụng"
    ],
    "tron_chay": ["bỏ chạy", "tẩu thoát", "rời khỏi hiện trường"],
    "vi_pham_nghiem_trong": ["vi phạm nghiêm trọng", "tái phạm", "vi phạm nhiều lần"],
    "khong_chap_hanh": ["không chấp hành", "cản trở", "chống đối"]
}

TAG_CONTENT_RULES = {
    "den_tin_hieu": {
        "positive": [
            "không chấp hành",
            "đèn tín hiệu",
            "tín hiệu giao thông",
            "vượt đèn"
        ],
        "negative": [
            "dừng xe",
            "đỗ xe",
            "che khuất",
            "dải phân cách"
        ],
        "skip_vehicle_text_filter": True
    },
    "dien_thoai": {
        "positive": [
            "điện thoại",
            "thiết bị điện tử",
            "thiết bị viễn thông",
            "thiết bị liên lạc"
        ],
        "negative": [
            "trẻ em",
            "ghế",
            "dây đai",
            "an toàn cho trẻ"
        ],
        "skip_vehicle_text_filter": True
    },
    "cho_hang": {
        "positive": [
            "tải trọng",
            "trọng tải",
            "khối lượng",
            "50%",
            "vượt quá tải"
        ]
    }
}


@dataclass
class ChunkMetadata:
    """Metadata for each chunk with point deduction"""
    article: int
    khoan: int
    diem: Optional[str]
    doc_id: Optional[str]
    tags: Set[str]
    is_escalation: bool
    escalation_refs: Set[Tuple[int, int, Optional[str]]]
    priority: int
    content: str
    penalty_min: Optional[int] = None
    penalty_max: Optional[int] = None
    point_deduction: Optional[int] = None
    license_suspension_months: Optional[Tuple[int, int]] = None  # (min, max) months
    references: Optional[List[dict]] = None  # Raw references from JSON


class TrafficLawRAGWithPoints:
    """Enhanced RAG Pipeline with License Point Deduction"""
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.chunks: List[ChunkMetadata] = []
        self.behavior_index: Dict[str, List[int]] = defaultdict(list)
        self.escalation_chunks: List[int] = []
        self.reference_index: Dict[Tuple[int, int, Optional[str]], List[int]] = defaultdict(list)
        self.doc_id_to_chunk_idx: Dict[str, int] = {}

        # Semantic retrieval state
        self.semantic_embeddings: Optional[np.ndarray] = None
        self.semantic_metadata: List[Dict[str, Any]] = []
        self.semantic_encoder = None
        self.semantic_index_config: Dict[str, Any] = {}
        self.semantic_search_enabled = False
        self.semantic_index_dir = Path(
            os.getenv(
                "SEMANTIC_INDEX_DIR",
                Path(__file__).resolve().parent / "semantic_index",
            )
        )
        self.semantic_top_k = int(os.getenv("SEMANTIC_TOP_K", "15"))
        self.semantic_min_score = float(os.getenv("SEMANTIC_MIN_SCORE", "0.35"))
        self.semantic_encoder_name = None
        
        self._load_and_process_data()
        self._setup_semantic_search()
    
    def _extract_tags(self, text: str) -> Set[str]:
        """Extract behavior tags from text"""
        text_lower = text.lower()
        tags = set()
        
        for tag, keywords in BEHAVIOR_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    tags.add(tag)
                    break

        if "khong_day_an_toan" in tags and "day_an_toan" not in tags:
            tags.add("day_an_toan")
            tags.discard("khong_day_an_toan")
        
        return tags
    
    def _filter_by_keyword_rules(
        self,
        chunks: List["ChunkMetadata"],
        query_tags: Set[str],
    ) -> List["ChunkMetadata"]:
        """Refine candidate chunks using tag-specific positive/negative keywords."""
        if not chunks:
            return chunks
        
        filtered_chunks = chunks
        for tag in query_tags:
            rules = TAG_CONTENT_RULES.get(tag)
            if not rules:
                continue
            
            positives = [kw.lower() for kw in rules.get("positive", [])]
            negatives = [kw.lower() for kw in rules.get("negative", [])]
            
            scored_chunks = []
            for chunk in filtered_chunks:
                content = (chunk.content or "").lower()
                positive_score = sum(1 for kw in positives if kw in content)
                negative_score = sum(1 for kw in negatives if kw in content)
                total_score = positive_score - negative_score
                scored_chunks.append((total_score, positive_score, chunk.penalty_max or 0, chunk.priority, chunk))
            
            # Determine best score; if all scores <=0 skip to avoid over-filtering
            best_score = max(score for score, _, _, _, _ in scored_chunks)
            if best_score <= 0:
                continue
            
            filtered_chunks = [
                chunk for score, pos_score, _, _, chunk in scored_chunks
                if score == best_score and pos_score > 0
            ]
            if not filtered_chunks:
                # Fallback to original if filtering eliminated everything
                filtered_chunks = [chunk for _, _, _, _, chunk in scored_chunks]
            else:
                print(f"   Applied keyword rules for tag '{tag}', remaining {len(filtered_chunks)} chunks")
        
        return filtered_chunks
    
    def _detect_vehicle_type(self, query: str) -> int:
        """Detect vehicle type from query (returns article number)"""
        query_lower = query.lower()
        
        # Check for xe mô tô / xe máy keywords first (more specific)
        moto_keywords = ['xe mô tô', 'xe máy', 'mô tô', 'xe gắn máy']
        if any(keyword in query_lower for keyword in moto_keywords):
            return 7  # Điều 7 for motorcycles
        
        # Helmet-related violations almost always apply to mô tô
        helmet_keywords = ['mũ bảo hiểm', 'không đội mũ', 'không đội nón', 'không đội mũ bảo hiểm']
        if any(keyword in query_lower for keyword in helmet_keywords):
            return 7
        
        # Seatbelt-specific phrases imply ô tô
        seatbelt_keywords = [
            'dây an toàn', 'dây đai an toàn', 'cài dây an toàn',
            'không thắt dây an toàn', 'không cài dây an toàn'
        ]
        if any(keyword in query_lower for keyword in seatbelt_keywords):
            return 6
        
        # Check for xe ô tô keywords
        car_keywords = ['xe ô tô', 'ô tô', 'xe hơi']
        if any(keyword in query_lower for keyword in car_keywords):
            return 6  # Điều 6 for cars
        
        # Default to car if no specific vehicle mentioned
        return 6
    
    def _extract_speed_range(self, query: str) -> Optional[int]:
        """Extract speed violation amount from query (in km/h)"""
        # Patterns for speed extraction
        patterns = [
            r'quá tốc độ\s+(\d+)\s*km',
            r'vượt tốc độ\s+(\d+)\s*km',
            r'chạy quá tốc\s*(?:độ)?\s+(\d+)\s*km',
            r'tốc độ\s+(\d+)\s*km'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return int(match.group(1))
        
        return None
    
    def _get_speed_violation_khoan(self, article: int, speed_kmh: int, has_accident: bool) -> Optional[int]:
        """
        Determine the appropriate khoản based on speed violation amount
        
        Article 6 (Ô tô):
        - khoản 4 điểm i: 5-10 km/h (800K-1M)
        - khoản 5: 10-20 km/h (4M-6M) 
        - khoản 6 điểm a: 20-35 km/h (6M-8M) ← 25km/h falls here
        - khoản 7 điểm a: > 35 km/h (12M-14M)
        - khoản 10: any speed + accident (20M-22M)
        
        Article 7 (Mô tô):
        - khoản 4 điểm a: 10-20 km/h (800K-1M)
        - khoản 8 điểm a: > 20 km/h (6M-8M) ← 25km/h falls here
        - khoản 10: any speed + accident (10M-14M)
        """
        if article == 6:  # Xe ô tô
            if has_accident:
                return 10  # Any speed + accident
            elif speed_kmh <= 10:
                return 4  # 5-10 km/h
            elif speed_kmh <= 20:
                return 5  # 10-20 km/h
            elif speed_kmh <= 35:
                return 6  # 20-35 km/h (25 falls here)
            else:
                return 7  # > 35 km/h
        
        elif article == 7:  # Xe mô tô
            if has_accident:
                return 10  # Any speed + accident
            elif speed_kmh <= 20:
                return 4  # 10-20 km/h
            else:
                return 8  # > 20 km/h (25 falls here)
        
        return None
    
    def _is_escalation_chunk(self, text: str) -> bool:
        """Check if chunk describes escalation rules"""
        text_lower = text.lower()
        escalation_patterns = [
            r'nâng mức',
            r'tăng mức',
            r'phạt cao hơn',
            r'cao hơn mức',
            r'quy định tại điều \d+ khoản \d+',
            r'các hành vi.*điểm [a-z]',
            r'một trong các hành vi'
        ]
        
        return any(re.search(pattern, text_lower) for pattern in escalation_patterns)
    
    def _extract_escalation_refs(self, text: str) -> Set[Tuple[int, int, Optional[str]]]:
        """Extract references from escalation chunks"""
        refs = set()
        
        # Pattern: Điều X khoản Y điểm Z
        pattern1 = re.compile(r'Điều\s+(\d+)\s+khoản\s+(\d+)\s+điểm\s+([a-z]|đ)', re.IGNORECASE)
        for match in pattern1.finditer(text):
            refs.add((int(match.group(1)), int(match.group(2)), match.group(3).lower()))
        
        # Pattern: Điều X khoản Y
        pattern2 = re.compile(r'Điều\s+(\d+)\s+khoản\s+(\d+)', re.IGNORECASE)
        for match in pattern2.finditer(text):
            if not any(ref[0] == int(match.group(1)) and ref[1] == int(match.group(2)) for ref in refs):
                refs.add((int(match.group(1)), int(match.group(2)), None))
        
        # Pattern: khoản X điểm Y (same article)
        pattern3 = re.compile(r'khoản\s+(\d+)\s+điểm\s+([a-z]|đ)', re.IGNORECASE)
        for match in pattern3.finditer(text):
            refs.add((None, int(match.group(1)), match.group(2).lower()))
        
        # Pattern: điểm a, b, c
        pattern4 = re.compile(r'điểm\s+([a-z]|đ)(?:\s*,\s*([a-z]|đ))*', re.IGNORECASE)
        for match in pattern4.finditer(text):
            letters = re.findall(r'\b([a-z]|đ)\b', match.group(0).lower())
            for letter in letters:
                refs.add((None, None, letter))
        
        return refs
    
    def _extract_penalty_amounts(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract penalty amounts from text (in thousands VND)"""
        patterns = [
            r'(\d+)\.(\d+)\.000\s*đồng',
            r'(\d+)\.(\d+)\s*triệu',
            r'(\d+)\s*triệu',
            r'(\d+)\s*đến\s*(\d+)\s*triệu'
        ]
        
        amounts = []
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                if 'đến' in match.group(0):
                    min_val = int(match.group(1)) * 1000
                    max_val = int(match.group(2)) * 1000
                    return min_val, max_val
                elif '.' in match.group(0) and 'triệu' not in match.group(0):
                    val = int(match.group(1) + match.group(2))
                    amounts.append(val)
                else:
                    val = int(match.group(1)) * 1000
                    amounts.append(val)
        
        if amounts:
            return min(amounts), max(amounts)
        
        return None, None
    
    def _extract_point_deduction(self, article: int, khoan: int, diem: Optional[str]) -> Optional[int]:
        """
        Extract license point deduction based on Article 6 khoản 16 and Article 7 khoản 13
        
        Article 6 (Ô tô) - khoản 16:
        - 2 điểm: khoản 3 (h,i); khoản 4 (a,b,c,d,đ,g); khoản 5 (a,b,c,d,đ,e,g,i,k,n,o)
        - 4 điểm: khoản 5 (h); khoản 6; khoản 7 (b); khoản 9 (b,c,d)
        - 6 điểm: khoản 5 (p); khoản 7 (a,c); khoản 8
        - 10 điểm: khoản 9 (a); khoản 10; khoản 11 (đ)
        
        Article 7 (Mô tô) - khoản 13:
        - 2 điểm: khoản 3 (b); khoản 5; khoản 6 (b,c,d)
        - 4 điểm: khoản 4 (đ); khoản 6 (a); khoản 7 (c,d,đ); khoản 8 (a)  ← 25km/h here!
        - 6 điểm: khoản 7 (b); khoản 9 (c)
        - 10 điểm: khoản 8 (b); khoản 10
        """
        if article == 6:  # Xe ô tô
            # 10 points
            if (khoan == 9 and diem == 'a') or khoan == 10 or (khoan == 11 and diem == 'đ'):
                return 10
            # 6 points
            elif (khoan == 5 and diem == 'p') or (khoan == 7 and diem in ['a', 'c']) or khoan == 8:
                return 6
            # 4 points
            elif (khoan == 5 and diem == 'h') or khoan == 6 or (khoan == 7 and diem == 'b') or (khoan == 9 and diem in ['b', 'c', 'd']):
                return 4
            # 2 points
            elif (khoan == 3 and diem in ['h', 'i']) or \
                 (khoan == 4 and diem in ['a', 'b', 'c', 'd', 'đ', 'g']) or \
                 (khoan == 5 and diem in ['a', 'b', 'c', 'd', 'đ', 'e', 'g', 'i', 'k', 'n', 'o']):
                return 2
        
        elif article == 7:  # Xe mô tô
            # 10 points - Note: khoản 8 điểm b (alcohol), not khoản 8 điểm a (speed)
            if (khoan == 8 and diem == 'b') or khoan == 10:
                return 10
            # 6 points
            elif (khoan == 7 and diem == 'b') or (khoan == 9 and diem == 'c'):
                return 6
            # 4 points - khoản 8 điểm a (speed >20km/h) is here!
            elif (khoan == 4 and diem == 'đ') or (khoan == 6 and diem == 'a') or \
                 (khoan == 7 and diem in ['c', 'd', 'đ']) or (khoan == 8 and diem == 'a'):
                return 4
            # 2 points
            elif (khoan == 3 and diem == 'b') or khoan == 5 or (khoan == 6 and diem in ['b', 'c', 'd']):
                return 2
        
        return None
    
    def _extract_license_suspension(self, article: int, khoan: int) -> Optional[Tuple[int, int]]:
        """
        Extract license suspension duration (in months) based on article and khoan
        Based on Nghị định 168 - each khoản specifies suspension duration
        """
        if article == 6:  # Xe ô tô
            if khoan == 5:
                return (1, 3)  # 1-3 months
            elif khoan == 6:
                return (2, 4)  # 2-4 months  
            elif khoan == 7:
                return (2, 4)  # 2-4 months
            elif khoan == 8:
                return (3, 5)  # 3-5 months
            elif khoan == 9:
                return (4, 6)  # 4-6 months
            elif khoan == 10:
                return (5, 7)  # 5-7 months
            elif khoan == 11:
                return (6, 8)  # 6-8 months
        
        elif article == 7:  # Xe mô tô
            if khoan == 4:
                return (1, 3)
            elif khoan == 5:
                return (1, 3)
            elif khoan == 6:
                return (2, 4)
            elif khoan == 7:
                return (2, 4)
            elif khoan == 8:
                return (3, 5)
            elif khoan == 9:
                return (4, 6)
            elif khoan == 10:
                return (5, 7)
            elif khoan == 11:
                return (22, 24)  # Wheelie/dangerous stunts - 22-24 months
        
        return None
    
    def _load_and_process_data(self):
        """Load and process the metadata file into chunks with point deduction"""
        print("Loading data from", self.data_path)
        
        with open(self.data_path, 'r', encoding='utf-8') as f:
            if self.data_path.endswith('.jsonl'):
                data = [json.loads(line) for line in f]
            else:
                data = json.load(f)
        
        print(f"   Found {len(data)} records")
        
        for idx, record in enumerate(data):
            content = record.get('content') or record.get('text') or record.get('diem_text', '')
            article = record.get('article_num') or record.get('article')
            khoan = record.get('khoan_num') or record.get('khoan')
            diem = record.get('diem_letter') or record.get('diem')
            doc_id = record.get('doc_id') or f"chunk_{idx}"
            
            if not content or not article or not khoan:
                continue
            
            # USE tags from JSON if available (more accurate), otherwise extract from content
            tags = set(record.get('tags', []))
            extracted_tags = self._extract_tags(content)
            if tags:
                tags.update(extracted_tags)
                # Normalize legacy tags to align with query extraction
                if "khong_day_an_toan" in tags and "day_an_toan" not in tags:
                    tags.add("day_an_toan")
                    tags.discard("khong_day_an_toan")
            else:
                tags = extracted_tags
            
            # USE is_escalation from JSON if available, otherwise detect
            is_escalation = record.get('is_escalation', False)
            if is_escalation is None:  # If not specified in JSON
                is_escalation = self._is_escalation_chunk(content)
            
            escalation_refs = set()
            if is_escalation:
                escalation_refs = self._extract_escalation_refs(content)
                filled_refs = set()
                for ref in escalation_refs:
                    if ref[0] is None:
                        filled_refs.add((article, ref[1] or khoan, ref[2]))
                    else:
                        filled_refs.add(ref)
                escalation_refs = filled_refs
            
            # USE penalty from JSON if available, otherwise extract
            penalty_min = record.get('penalty_min')
            penalty_max = record.get('penalty_max')
            if penalty_min is None or penalty_max is None:
                penalty_min, penalty_max = self._extract_penalty_amounts(content)
            
            point_deduction = self._extract_point_deduction(article, khoan, diem)
            license_suspension = self._extract_license_suspension(article, khoan)
            
            # Get references from JSON if available
            references = record.get('references', []) if record.get('references') else []
            
            priority = 50
            if is_escalation:
                if any(keyword in content.lower() for keyword in ESCALATION_INDICATORS["gay_tai_nan"]):
                    priority = 100
                elif escalation_refs:
                    priority = 90
                else:
                    priority = 80
            
            chunk = ChunkMetadata(
                article=article,
                khoan=khoan,
                diem=diem,
                doc_id=doc_id,
                tags=tags,
                is_escalation=is_escalation,
                escalation_refs=escalation_refs,
                priority=priority,
                content=content,
                penalty_min=penalty_min,
                penalty_max=penalty_max,
                point_deduction=point_deduction,
                license_suspension_months=license_suspension,
                references=references
            )
            
            chunk_idx = len(self.chunks)
            self.chunks.append(chunk)
            if doc_id not in self.doc_id_to_chunk_idx:
                self.doc_id_to_chunk_idx[doc_id] = chunk_idx
            
            for tag in tags:
                self.behavior_index[tag].append(chunk_idx)
            
            if is_escalation:
                self.escalation_chunks.append(chunk_idx)
            
            ref = (article, khoan, diem)
            self.reference_index[ref].append(chunk_idx)
        
        print(f"Processed {len(self.chunks)} chunks")
        print(f"   Behavior tags: {len(self.behavior_index)}")
        print(f"   Escalation chunks: {len(self.escalation_chunks)}")
        print(f"   Chunks with point deduction: {sum(1 for c in self.chunks if c.point_deduction)}")
    
    def retrieve(self, query: str) -> dict:
        """Retrieve relevant chunks with full details including point deduction"""
        
        query_tags = self._extract_tags(query)
        query_lower = query.lower()
        has_tai_nan = any(keyword in query_lower for keyword in ESCALATION_INDICATORS["gay_tai_nan"])
        load_keywords = ['tải trọng', 'trọng tải', 'quá tải', 'vượt tải']
        is_load_query = any(keyword in query_lower for keyword in load_keywords)
        
        # SPECIAL CASE: For individuals, "không mang" (not carrying) is legally same as "không có" (not having)
        # Only business transport has special lower penalty for "không mang"
        if 'khong_mang_bang_lai' in query_tags and 'van_tai' not in query_tags:
            query_tags.add('khong_bang_lai')  # Also match "không có" provisions
        
        # Detect subject type (individual vs organization)
        is_organization = any(keyword in query_lower for keyword in ['tổ chức', 'doanh nghiệp', 'công ty', 'cơ sở', 'đơn vị'])
        
        # Detect vehicle type and speed violation
        vehicle_article = self._detect_vehicle_type(query)
        speed_kmh = self._extract_speed_range(query)
        
        # Detect engine size (for motorcycles)
        engine_size_tag = None
        if re.search(r'(\d+)\s*cc', query_lower, re.IGNORECASE):
            cc_match = re.search(r'(\d+)\s*cc', query_lower, re.IGNORECASE)
            cc_value = int(cc_match.group(1))
            if cc_value <= 125:
                engine_size_tag = 'engine_125cc_or_less'
                # Don't add to query_tags - only use for filtering, not matching
            else:
                engine_size_tag = 'engine_over_125cc'
                # Don't add to query_tags - only use for filtering, not matching
        
        print(f"\nQuery: {query}")
        print(f"   Detected tags: {query_tags}")
        print(f"   Subject: {'Tổ chức' if is_organization else 'Cá nhân'}")
        print(f"   Vehicle type: {'Xe ô tô (Điều 6)' if vehicle_article == 6 else 'Xe mô tô (Điều 7)'}")
        print(f"   Has tai nạn: {has_tai_nan}")
        if speed_kmh:
            print(f"   Speed violation: {speed_kmh} km/h")
        if engine_size_tag:
            print(f"   Engine size: {engine_size_tag}")
        
        if not query_tags:
            if self.semantic_search_enabled:
                print("   No behavior tags detected -> relying on semantic retrieval")
            else:
                return {
                    "status": "no_tags",
                    "message": "Không phát hiện hành vi cụ thể trong câu hỏi"
                }
        
        # If speed violation detected, find the appropriate khoan
        target_khoan = None
        target_article = None
        if speed_kmh and "qua_toc_do" in query_tags:
            target_article = vehicle_article
            target_khoan = self._get_speed_violation_khoan(vehicle_article, speed_kmh, has_tai_nan)
            if target_khoan:
                print(f"   Target: Điều {target_article} khoản {target_khoan} for {speed_kmh}km/h")
        
        behavior_chunk_indices = set()
        # Tag-based retrieval
        for tag in query_tags:
            if tag in self.behavior_index:
                behavior_chunk_indices.update(self.behavior_index[tag])
        
        if behavior_chunk_indices:
            print(f"   Tag-based retrieval found {len(behavior_chunk_indices)} chunks")

        semantic_chunk_indices: List[Tuple[int, float]] = []
        if self.semantic_search_enabled:
            print("   Running semantic search...")
            semantic_chunk_indices = self._semantic_search(query, top_k=self.semantic_top_k)
            if semantic_chunk_indices:
                semantic_log = ", ".join(
                    f"{self.chunks[idx].article}-{self.chunks[idx].khoan}:{score:.2f}"
                    for idx, score in semantic_chunk_indices[:5]
                )
                print(f"   Semantic search found {len(semantic_chunk_indices)} chunks: {semantic_log}")
                behavior_chunk_indices.update(idx for idx, _ in semantic_chunk_indices)
            else:
                print("   Semantic retrieval returned no confident matches")
        
        if not behavior_chunk_indices:
            return {
                "status": "no_chunks",
                "message": "Không tìm thấy điều luật liên quan"
            }
        
        behavior_chunks = [self.chunks[idx] for idx in behavior_chunk_indices]
        print(f"   Found {len(behavior_chunks)} behavior chunks")
        
        # DEBUG: Check if ND168_art18_k2_d is in behavior_chunks
        k2d_in_behaviors = any(c.article == 18 and c.khoan == 2 and c.diem == 'd' for c in behavior_chunks)
        if k2d_in_behaviors:
            print(f"   DEBUG: ND168_art18_k2_d IS in behavior_chunks")
        else:
            print(f"   DEBUG: ND168_art18_k2_d NOT in behavior_chunks")
        
        # FILTER BY SUBJECT TYPE: Default to individual (Điều 6-21), unless "tổ chức" mentioned
        if not is_organization:
            # Individual violations: Điều 6-21 (traffic violations by individuals)
            individual_chunks = [
                c for c in behavior_chunks
                if (6 <= c.article <= 21) or c.article in CROSS_VEHICLE_ARTICLES
            ]
            if individual_chunks:
                behavior_chunks = individual_chunks
                print(f"   Filtered to {len(behavior_chunks)} individual chunks (Điều 6-21)")
        else:
            # Organization violations: Điều 30+ (business/organization violations)
            org_chunks = [c for c in behavior_chunks if c.article >= 30]
            if org_chunks:
                behavior_chunks = org_chunks
                print(f"   Filtered to {len(behavior_chunks)} organization chunks (Điều 30+)")
        
        # FILTER BY VEHICLE TYPE: If vehicle type detected, prioritize matching article
        # This prevents xe ô tô queries from matching Điều 7 (mô tô) rules
        original_behavior_chunks = behavior_chunks[:]
        cross_vehicle_tags = {"dua_xe", "co_vu_dua_xe"}
        skip_vehicle_article_filter = False
        skip_reason = ""
        if is_load_query:
            skip_vehicle_article_filter = True
            skip_reason = "load-related query"
        elif query_tags & cross_vehicle_tags:
            skip_vehicle_article_filter = True
            skip_reason = "đua xe áp dụng chung (Điều 35)"

        if not skip_vehicle_article_filter:
            vehicle_filtered_chunks = [c for c in behavior_chunks if c.article == vehicle_article]
            if vehicle_filtered_chunks:
                behavior_chunks = vehicle_filtered_chunks
                print(f"   Filtered to {len(behavior_chunks)} chunks for vehicle article {vehicle_article}")
                # Debug: show what's in behavior_chunks
                for c in behavior_chunks:
                    print(f"      - Điều {c.article} khoản {c.khoan} điểm {c.diem}: is_escalation={c.is_escalation}, penalty={c.penalty_min}-{c.penalty_max}")
        else:
            print(f"   Skipped strict vehicle filtering ({skip_reason or 'special-case query'})")
        
        # Additional semantic filtering using query cues
        skip_vehicle_text_filter = any(
            TAG_CONTENT_RULES.get(tag, {}).get("skip_vehicle_text_filter")
            for tag in query_tags
        )

        if behavior_chunks:
            content_filters_applied = False
            # Prioritize chunks whose text mentions the detected vehicle type explicitly
            if vehicle_article == 7 and not skip_vehicle_text_filter:
                moto_terms = ['xe mô tô', 'xe gắn máy', 'xe máy', 'mô tô', 'xe hai bánh']
                moto_specific = [
                    c for c in behavior_chunks
                    if any(term in (c.content or "").lower() for term in moto_terms)
                ]
                if moto_specific:
                    behavior_chunks = moto_specific
                    content_filters_applied = True
                    print(f"   Filtered to {len(behavior_chunks)} mô tô chunks by text match")
            elif vehicle_article == 6 and not skip_vehicle_text_filter:
                car_terms = ['xe ô tô', 'ô tô', 'xe hơi', 'xe tải', 'xe khách']
                car_specific = [
                    c for c in behavior_chunks
                    if any(term in (c.content or "").lower() for term in car_terms)
                ]
                if car_specific:
                    behavior_chunks = car_specific
                    content_filters_applied = True
                    print(f"   Filtered to {len(behavior_chunks)} ô tô chunks by text match")

            # Focus on overload/tải trọng violations when query mentions them
            if is_load_query:
                load_terms = ['tải trọng', 'trọng tải', 'khối lượng', 'quá tải', 'quá khổ']
                load_specific = [
                    c for c in behavior_chunks
                    if any(term in (c.content or "").lower() for term in load_terms)
                ]
                if load_specific:
                    behavior_chunks = load_specific
                    content_filters_applied = True
                    print(f"   Filtered to {len(behavior_chunks)} overload chunks by content")
                else:
                    # fallback to original chunks if filtering removed everything
                    behavior_chunks = original_behavior_chunks
                    print("   No overload chunk found by content; reverting to original behavior set")

            # Focus on ngược chiều violations
            if 'ngược chiều' in query_lower:
                reverse_specific = [
                    c for c in behavior_chunks
                    if 'ngược chiều' in (c.content or "").lower()
                ]
                if reverse_specific:
                    behavior_chunks = reverse_specific
                    content_filters_applied = True
                    print(f"   Filtered to {len(behavior_chunks)} ngược chiều chunks by content")

            # Focus on đường cấm violations
            if any(keyword in query_lower for keyword in ['đường cấm', 'khu cấm', 'cấm đường']):
                restricted_terms = ['đường cấm', 'khu vực cấm', 'cấm đi', 'khu cấm']
                restricted_specific = [
                    c for c in behavior_chunks
                    if any(term in (c.content or "").lower() for term in restricted_terms)
                ]
                if restricted_specific:
                    behavior_chunks = restricted_specific
                    content_filters_applied = True
                    print(f"   Filtered to {len(behavior_chunks)} đường cấm chunks by content")

            # Focus on đèn tín hiệu violations
            if 'den_tin_hieu' in query_tags:
                light_terms = ['đèn tín hiệu', 'tín hiệu giao thông', 'đèn đỏ']
                light_specific = [
                    c for c in behavior_chunks
                    if any(term in (c.content or "").lower() for term in light_terms)
                ]
                if light_specific:
                    behavior_chunks = light_specific
                    content_filters_applied = True
                    print(f"   Filtered to {len(behavior_chunks)} đèn tín hiệu chunks by content")

            # Focus on điện thoại / thiết bị cầm tay
            if 'dien_thoai' in query_tags:
                phone_terms = ['điện thoại', 'thiết bị điện tử', 'thiết bị phát tín hiệu', 'thiết bị liên lạc', 'dùng điện thoại']
                phone_specific = [
                    c for c in behavior_chunks
                    if any(term in (c.content or "").lower() for term in phone_terms)
                ]
                if phone_specific:
                    behavior_chunks = phone_specific
                    content_filters_applied = True
                    print(f"   Filtered to {len(behavior_chunks)} điện thoại chunks by content")

            if content_filters_applied:
                # Re-order after content-based filtering to keep highest penalty first
                behavior_chunks.sort(key=lambda c: (c.penalty_max or 0, c.priority), reverse=True)

        # Apply tag-specific keyword rules to disambiguate similar chunks
        behavior_chunks = self._filter_by_keyword_rules(behavior_chunks, query_tags)

        # If we have a target khoan for speed, further filter by khoan
        if target_khoan and target_article:
            speed_filtered_chunks = [
                c for c in behavior_chunks 
                if c.article == target_article and c.khoan == target_khoan
            ]
            if speed_filtered_chunks:
                behavior_chunks = speed_filtered_chunks
                print(f"   Filtered to {len(behavior_chunks)} chunks matching Điều {target_article} khoản {target_khoan}")
        
        behavior_refs = set()
        for chunk in behavior_chunks:
            behavior_refs.add((chunk.article, chunk.khoan, chunk.diem))
        
        # Collect ALL matching chunks (both base behaviors and escalations)
        matched_chunks = []
        
        # FIRST: Add base behavior chunks (non-escalation) that match tags
        for chunk in behavior_chunks:
            if not chunk.is_escalation and query_tags & chunk.tags:
                matched_chunks.append(chunk)
                print(f"   Matched base behavior: Điều {chunk.article} khoản {chunk.khoan} điểm {chunk.diem}")
        
        # SECOND: Add escalation chunks
        for esc_idx in self.escalation_chunks:
            esc_chunk = self.chunks[esc_idx]
            
            # ALWAYS filter by vehicle article first
            if esc_chunk.article != vehicle_article:
                continue
            
            # If we have target khoan from speed detection, also check that
            if target_khoan and esc_chunk.khoan != target_khoan:
                continue
            
            ref_match = bool(behavior_refs & esc_chunk.escalation_refs)
            tag_match = bool(query_tags & esc_chunk.tags)
            tai_nan_match = has_tai_nan and esc_chunk.priority == 100
            
            if ref_match or tag_match or tai_nan_match:
                matched_chunks.append(esc_chunk)
                print(f"   Matched escalation: Điều {esc_chunk.article} khoản {esc_chunk.khoan} (priority={esc_chunk.priority})")
        
        if matched_chunks:
            # STRATEGY: Select chunk with best match
            # Priority:
            # 1. For accidents (tai nạn): Highest penalty (escalation)
            # 2. For normal violations: Best text match + appropriate penalty
            
            # Filter out chunks with no penalty info
            chunks_with_penalty = [c for c in matched_chunks if c.penalty_max]
            
            # Check for exact phrase matches in query
            # This helps distinguish "không gắn biển số" from "gắn biển số không đúng"
            exact_matches = []
            for chunk in chunks_with_penalty:
                chunk_text = chunk.content.lower()
                # Check if key phrases from query appear in chunk
                query_phrases = []
                if "không gắn biển số" in query_lower or "không có biển số" in query_lower:
                    query_phrases = ["không gắn biển số"]
                elif "gắn biển số không đúng" in query_lower or "biển số giả" in query_lower:
                    query_phrases = ["gắn biển số không đúng", "không do cơ quan"]
                
                if query_phrases:
                    for phrase in query_phrases:
                        if phrase in chunk_text:
                            exact_matches.append(chunk)
                            break
            
            # Context-based location filtering for violations
            # Default: prefer general violations over tunnel-specific unless explicitly mentioned
            has_tunnel_keyword = "trong hầm" in query_lower or "hầm đường" in query_lower
            has_road_keyword = any(road_kw in query_lower for road_kw in ["ngoài đường", "trên đường", "đường phố", "ban đêm", "ban ngày"])
            
            if has_tunnel_keyword:
                # Explicitly mentions tunnel - prefer tunnel violations
                tunnel_chunks = [c for c in chunks_with_penalty if "hầm" in c.content.lower()]
                if tunnel_chunks:
                    chunks_with_penalty = tunnel_chunks
                    exact_matches = [c for c in exact_matches if "hầm" in c.content.lower()]
                    print(f"   Preferred tunnel-specific violations (query mentions tunnel)")
            elif has_road_keyword or not has_tunnel_keyword:
                # Explicitly mentions road OR no location context - exclude tunnel violations (default to general)
                chunks_with_penalty = [c for c in chunks_with_penalty 
                                      if "hầm" not in c.content.lower() and "hầm đường bộ" not in c.content.lower()]
                exact_matches = [c for c in exact_matches 
                               if "hầm" not in c.content.lower() and "hầm đường bộ" not in c.content.lower()]
                reason = "road" if has_road_keyword else "default to general case"
                print(f"   Excluded tunnel-specific violations ({reason})")
            
            # If we have exact matches and no accident, prefer those over highest penalty
            if exact_matches and not has_tai_nan:
                # Among exact matches, prefer the article that matches vehicle type
                # For xe ô tô: prefer Điều 13 (car equipment) over Điều 16 (other vehicles)
                # For xe mô tô: prefer Điều 14 (motorcycle equipment)
                preferred_article = 13 if vehicle_article == 6 else 14
                
                vehicle_specific = [c for c in exact_matches if c.article == preferred_article]
                if vehicle_specific:
                    # Sort by penalty to get the base violation (lower penalty)
                    vehicle_specific.sort(key=lambda c: c.penalty_max or 0)
                    primary_chunk = vehicle_specific[0]
                    print(f"   Selected exact match for vehicle article {preferred_article}: Điều {primary_chunk.article} khoản {primary_chunk.khoan} ({primary_chunk.penalty_max//1000}K)")
                else:
                    # No vehicle-specific match, use any exact match (lowest penalty)
                    exact_matches.sort(key=lambda c: c.penalty_max or 0)
                    primary_chunk = exact_matches[0]
                    print(f"   Selected exact match: Điều {primary_chunk.article} khoản {primary_chunk.khoan} ({primary_chunk.penalty_max//1000}K)")
            
            elif has_tai_nan and chunks_with_penalty:
                # Special case: Check for khoản 13 (reckless driving + accident)
                # Khoản 13 is for khoản 12 violations (lạng lách, đánh võng) causing accidents
                khoan_13_chunks = [c for c in chunks_with_penalty if c.khoan == 13]
                khoan_12_chunks = [c for c in chunks_with_penalty if c.khoan == 12]
                
                # If both khoản 12 and khoản 13 are matched, prefer khoản 13 (accident escalation of khoản 12)
                if khoan_13_chunks and khoan_12_chunks:
                    primary_chunk = khoan_13_chunks[0]
                    print(f"   Selected khoản 13 (reckless driving + accident): Điều {primary_chunk.article} khoản {primary_chunk.khoan} ({primary_chunk.penalty_max//1000}K)")
                else:
                    # Normal accident escalation logic
                    # For accidents, prefer escalation chunks (is_escalation=True) first
                    # This ensures khoản 10 (escalation, 20M-22M) is selected over other base behaviors
                    escalation_chunks = [c for c in chunks_with_penalty if c.is_escalation]
                    base_chunks = [c for c in chunks_with_penalty if not c.is_escalation]
                    
                    if escalation_chunks:
                        # If there are khoản 10 chunks, check if they have references matching base behaviors
                        khoan_10_chunks = [c for c in escalation_chunks if c.khoan == 10]
                        
                        if len(khoan_10_chunks) > 1:
                            # Try to select the most specific one based on references
                            # Check which base behaviors were matched
                            base_khoan_diem = set()
                            for chunk in base_chunks:
                                if chunk.diem:
                                    base_khoan_diem.add((chunk.khoan, chunk.diem))
                            
                            # Check which khoản 10 chunk's references match base behaviors
                            best_match = None
                            for chunk in khoan_10_chunks:
                                if chunk.references:
                                    # khoản 10 điểm b has many references, điểm a has none
                                    # If we matched behaviors from khoản 1-9, prefer điểm b
                                    if base_khoan_diem:
                                        for ref in chunk.references:
                                            ref_tuple = (ref.get('khoan'), ref.get('diem'))
                                            if ref_tuple in base_khoan_diem:
                                                best_match = chunk
                                                print(f"   Found reference match: khoản {ref['khoan']} điểm {ref['diem']}")
                                                break
                                    if best_match:
                                        break
                            
                            if best_match:
                                primary_chunk = best_match
                            else:
                                # Sort by priority first, then penalty
                                escalation_chunks.sort(key=lambda x: (x.priority, x.penalty_max), reverse=True)
                                primary_chunk = escalation_chunks[0]
                        else:
                            # Sort escalations by priority first, then penalty
                            escalation_chunks.sort(key=lambda x: (x.priority, x.penalty_max), reverse=True)
                            primary_chunk = escalation_chunks[0]
                        
                        print(f"   Selected tai nạn escalation (is_escalation=True): Điều {primary_chunk.article} khoản {primary_chunk.khoan} điểm {primary_chunk.diem or 'None'} ({primary_chunk.penalty_max//1000}K)")
                    else:
                        # Fallback to base chunks sorted by penalty
                        base_chunks.sort(key=lambda x: x.penalty_max, reverse=True)
                        primary_chunk = base_chunks[0]
                        print(f"   Selected tai nạn base chunk: Điều {primary_chunk.article} khoản {primary_chunk.khoan} ({primary_chunk.penalty_max//1000}K)")
            else:
                # No tai nạn - normal violation
                # If we already found exact matches via phrase matching, use them (set earlier)
                if 'primary_chunk' not in locals():
                    # PRIORITIZE SPECIFIC TAGS over general ones
                    # Define specific tag hierarchy (more specific first)
                    specific_tags = [
                        'co_vu_dua_xe',         # Most specific: supporting/gathering for racing (1-2M)
                        'khong_mang_bang_lai',  # Most specific: not carrying license (200K-300K)
                        'khong_bang_lai',       # Specific: not having license (2-4M, 6-8M)
                        'khong_bien_so',        # Specific: no license plate
                        'dua_xe',               # Specific: racing (40-50M or confiscation)
                        'khong_giay_to',        # General: no documents
                    ]
                    
                    # Try to filter by most specific tag first
                    filtered_by_specific_tag = chunks_with_penalty
                    for specific_tag in specific_tags:
                        if specific_tag in query_tags:
                            # Filter to only chunks with this specific tag
                            tag_filtered = [c for c in chunks_with_penalty if specific_tag in c.tags]
                            if tag_filtered:
                                filtered_by_specific_tag = tag_filtered
                                print(f"   Filtered to {len(tag_filtered)} chunks with specific tag '{specific_tag}'")
                                
                                # ADDITIONAL FILTERING: For cross-cutting articles, filter by vehicle type in text
                                # Skip vehicle filtering for Điều 35 (racing) - applies to all vehicles
                                if vehicle_article in [6, 7] and not any(c.article == 35 for c in tag_filtered):
                                    vehicle_specific = []
                                    for chunk in tag_filtered:
                                        chunk_text = chunk.content.lower()
                                        # Check if chunk mentions the correct vehicle type
                                        if vehicle_article == 6:  # Cars
                                            if 'xe ô tô' in chunk_text or 'ô tô' in chunk_text:
                                                vehicle_specific.append(chunk)
                                        elif vehicle_article == 7:  # Motorcycles
                                            if 'xe mô tô' in chunk_text or 'mô tô' in chunk_text:
                                                vehicle_specific.append(chunk)
                                            else:
                                                print(f"      - Filtered OUT Điều {chunk.article} k{chunk.khoan} điểm {chunk.diem}: no 'xe mô tô' in text")
                                    
                                    if vehicle_specific:
                                        filtered_by_specific_tag = vehicle_specific
                                        print(f"   Further filtered to {len(vehicle_specific)} chunks matching vehicle type (Điều {vehicle_article})")
                                
                                break  # Use the most specific tag match
                    
                    # SPECIAL CASE: If filtered by 'khong_mang_bang_lai' but query has NO 'van_tai',
                    # and all results are business transport (van_tai), fall back to 'khong_bang_lai'
                    # because for individuals, "không mang" is treated same as "không có" in the law
                    if ('khong_mang_bang_lai' in query_tags and 'van_tai' not in query_tags and 
                        filtered_by_specific_tag and all('van_tai' in c.tags for c in filtered_by_specific_tag)):
                        print(f"   All 'khong_mang_bang_lai' results are business transport, falling back to 'khong_bang_lai'")
                        # Retry with khong_bang_lai tag - search in ALL matched_chunks, not just chunks_with_penalty
                        tag_filtered = [c for c in matched_chunks if 'khong_bang_lai' in c.tags]
                        if tag_filtered:
                            filtered_by_specific_tag = tag_filtered
                            print(f"   Filtered to {len(tag_filtered)} chunks with 'khong_bang_lai' tag")
                            for c in tag_filtered:
                                print(f"      - Điều {c.article} k{c.khoan} điểm {c.diem}: {c.penalty_min}-{c.penalty_max}")
                            
                            # Apply vehicle filtering again
                            if vehicle_article in [6, 7]:
                                vehicle_specific = []
                                for chunk in tag_filtered:
                                    chunk_text = chunk.content.lower()
                                    if vehicle_article == 6 and ('xe ô tô' in chunk_text or 'ô tô' in chunk_text):
                                        vehicle_specific.append(chunk)
                                    elif vehicle_article == 7 and ('xe mô tô' in chunk_text or 'mô tô' in chunk_text):
                                        vehicle_specific.append(chunk)
                                
                                if vehicle_specific:
                                    filtered_by_specific_tag = vehicle_specific
                                    print(f"   Further filtered to {len(vehicle_specific)} chunks matching vehicle type")
                    
                    # ENGINE SIZE FILTERING: If engine size detected, filter to matching provisions
                    if engine_size_tag and filtered_by_specific_tag:
                        engine_filtered = [c for c in filtered_by_specific_tag if engine_size_tag in c.tags]
                        if engine_filtered:
                            filtered_by_specific_tag = engine_filtered
                            print(f"   Further filtered to {len(engine_filtered)} chunks matching engine size ({engine_size_tag})")
                    
                    # SPECIAL CASE: If van_tai tag is detected, prefer chunks with van_tai tag (business transport)
                    # Business transport usually has LOWER penalties than individual violations
                    if 'van_tai' in query_tags and filtered_by_specific_tag:
                        van_tai_chunks = [c for c in filtered_by_specific_tag if 'van_tai' in c.tags]
                        if van_tai_chunks:
                            filtered_by_specific_tag = van_tai_chunks
                            print(f"   Further filtered to {len(van_tai_chunks)} business transport chunks (van_tai)")
                            # For business transport, prefer LOWEST penalty (not highest)
                            filtered_by_specific_tag.sort(key=lambda x: x.penalty_max)
                            primary_chunk = filtered_by_specific_tag[0]
                            print(f"   Selected business transport chunk with lowest penalty: Điều {primary_chunk.article} khoản {primary_chunk.khoan} ({primary_chunk.penalty_max//1000}K)")
                    
                    # For normal queries without exact match
                    if 'primary_chunk' not in locals():
                        if filtered_by_specific_tag:
                            # SPECIAL: For "không mang" queries (not carrying license), prefer LOWEST penalty
                            # as conservative default (without engine size info, assume lower tier)
                            if 'khong_mang_bang_lai' in query_tags and 'van_tai' not in query_tags:
                                # Individual not carrying license - prefer lower penalty tier
                                filtered_by_specific_tag.sort(key=lambda x: x.penalty_max)
                                primary_chunk = filtered_by_specific_tag[0]
                                print(f"   Selected chunk with lowest penalty (không mang - individual): Điều {primary_chunk.article} khoản {primary_chunk.khoan} ({primary_chunk.penalty_max//1000}K)")
                            else:
                                # For other queries, prefer highest penalty (most specific)
                                filtered_by_specific_tag.sort(key=lambda x: x.penalty_max, reverse=True)
                                primary_chunk = filtered_by_specific_tag[0]
                                print(f"   Selected chunk with highest penalty: Điều {primary_chunk.article} khoản {primary_chunk.khoan} ({primary_chunk.penalty_max//1000}K)")
                        else:
                            # Fallback to highest priority
                            matched_chunks.sort(key=lambda x: x.priority, reverse=True)
                            primary_chunk = matched_chunks[0]
                            print(f"   Selected by priority {primary_chunk.priority}")
        else:
            # No escalations matched, use first behavior chunk
            primary_chunk = behavior_chunks[0]
            print(f"   No escalation, using base behavior chunk")
        
        penalty_info = None
        if primary_chunk.penalty_min or primary_chunk.penalty_max:
            penalty_info = {
                "min": primary_chunk.penalty_min,
                "max": primary_chunk.penalty_max,
                "text": self._format_penalty(primary_chunk.penalty_min, primary_chunk.penalty_max)
            }
        
        suspension_info = None
        if primary_chunk.license_suspension_months:
            min_months, max_months = primary_chunk.license_suspension_months
            suspension_info = {
                "min_months": min_months,
                "max_months": max_months,
                "text": f"Tước GPLX từ {min_months} đến {max_months} tháng"
            }
        
        related_candidates: List[ChunkMetadata] = []
        if matched_chunks:
            related_candidates = [c for c in matched_chunks if c != primary_chunk]
            # Prioritize chunks with penalty information
            related_candidates.sort(key=lambda c: (c.penalty_max or 0), reverse=True)
        
        return {
            "status": "success",
            "primary_chunk": {
                "reference": f"Điều {primary_chunk.article} khoản {primary_chunk.khoan}" + 
                            (f" điểm {primary_chunk.diem}" if primary_chunk.diem else ""),
                "content": primary_chunk.content,
                "tags": list(primary_chunk.tags),
                "is_escalation": primary_chunk.is_escalation,
                "priority": primary_chunk.priority,
                "penalty": penalty_info,
                "point_deduction": primary_chunk.point_deduction,
                "license_suspension": suspension_info
            },
            "related_chunks": [
                {
                    "reference": f"Điều {chunk.article} khoản {chunk.khoan}" + 
                                (f" điểm {chunk.diem}" if chunk.diem else ""),
                    "content": (chunk.content[:200] + "...") if len(chunk.content) > 200 else chunk.content,
                    "tags": list(chunk.tags),
                    "penalty": {
                        "min": chunk.penalty_min,
                        "max": chunk.penalty_max,
                        "text": self._format_penalty(chunk.penalty_min, chunk.penalty_max)
                    } if (chunk.penalty_min or chunk.penalty_max) else None,
                    "point_deduction": chunk.point_deduction,
                    "license_suspension": {
                        "min_months": chunk.license_suspension_months[0],
                        "max_months": chunk.license_suspension_months[1],
                        "text": f"Tước GPLX từ {chunk.license_suspension_months[0]} đến {chunk.license_suspension_months[1]} tháng"
                    } if chunk.license_suspension_months else None
                }
                for chunk in related_candidates[:3]
            ],
            "escalations_applied": len([c for c in matched_chunks if c.is_escalation])
        }

    # ------------------------------------------------------------------ Semantic
    def _setup_semantic_search(self) -> None:
        """Load semantic index from disk if available."""
        embeddings_path = self.semantic_index_dir / "embeddings.npy"
        metadata_path = self.semantic_index_dir / "metadata.json"
        config_path = self.semantic_index_dir / "config.json"

        if not embeddings_path.exists() or not metadata_path.exists():
            print(f"[semantic] No index found in {self.semantic_index_dir}, skip semantic retrieval.")
            return

        try:
            raw_embeddings = np.load(embeddings_path)
            with metadata_path.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
            config = {}
            if config_path.exists():
                with config_path.open("r", encoding="utf-8") as f:
                    config = json.load(f)
            if raw_embeddings.shape[0] != len(metadata):
                raise ValueError("Embeddings count does not match metadata entries.")

            filtered_embeddings = []
            filtered_metadata = []
            dropped = 0
            for emb, meta in zip(raw_embeddings, metadata):
                doc_id = meta.get("doc_id")
                if doc_id not in self.doc_id_to_chunk_idx:
                    dropped += 1
                    continue
                filtered_embeddings.append(emb.astype("float32"))
                filtered_metadata.append(meta)

            if not filtered_embeddings:
                print("[semantic] Index does not overlap with current chunks.")
                return

            self.semantic_embeddings = np.stack(filtered_embeddings)
            self.semantic_metadata = filtered_metadata
            self.semantic_index_config = config or {}
            self.semantic_encoder_name = self.semantic_index_config.get("model_name", SEMANTIC_DEFAULT_MODEL)

            if SentenceTransformer is None:
                print("[semantic] sentence-transformers not installed -> semantic retrieval disabled.")
                return

            self.semantic_search_enabled = True
            print(f"[semantic] Loaded {len(self.semantic_metadata)} indexed chunks (dropped {dropped}).")
        except Exception as exc:
            print(f"[semantic] Failed to load semantic index: {exc}")
            self.semantic_search_enabled = False

    def _get_semantic_encoder(self):
        if not self.semantic_search_enabled:
            return None
        if self.semantic_encoder is not None:
            return self.semantic_encoder
        if SentenceTransformer is None:
            print("[semantic] sentence-transformers unavailable at runtime.")
            self.semantic_search_enabled = False
            return None
        model_name = self.semantic_encoder_name or SEMANTIC_DEFAULT_MODEL
        try:
            self.semantic_encoder = SentenceTransformer(model_name)
            print(f"[semantic] Loaded encoder '{model_name}'.")
        except Exception as exc:
            print(f"[semantic] Failed to load encoder '{model_name}': {exc}")
            self.semantic_search_enabled = False
            self.semantic_encoder = None
        return self.semantic_encoder

    def _semantic_search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        if not self.semantic_search_enabled or self.semantic_embeddings is None:
            return []
        encoder = self._get_semantic_encoder()
        if encoder is None:
            return []
        try:
            query_emb = encoder.encode(
                query,
                convert_to_numpy=True,
                normalize_embeddings=self.semantic_index_config.get("normalize_embeddings", True),
            ).astype("float32")
        except Exception as exc:
            print(f"[semantic] Encoding failed: {exc}")
            return []

        if query_emb.ndim > 1:
            query_emb = query_emb[0]

        if not self.semantic_index_config.get("normalize_embeddings", True):
            norm = np.linalg.norm(query_emb)
            if norm:
                query_emb = query_emb / norm

        scores = self.semantic_embeddings @ query_emb
        if scores.size == 0:
            return []

        k = min(top_k, scores.shape[0])
        top_idx = np.argpartition(scores, -k)[-k:]
        sorted_idx = top_idx[np.argsort(scores[top_idx])[::-1]]

        results: List[Tuple[int, float]] = []
        for idx in sorted_idx:
            score = float(scores[idx])
            if score < self.semantic_min_score:
                continue
            doc_id = self.semantic_metadata[idx].get("doc_id")
            chunk_idx = self.doc_id_to_chunk_idx.get(doc_id)
            if chunk_idx is None:
                continue
            results.append((chunk_idx, score))
        return results
    
    def _format_penalty(self, min_val: Optional[int], max_val: Optional[int]) -> str:
        """Format penalty amount in Vietnamese"""
        if not min_val and not max_val:
            return "Chưa xác định"
        
        def format_amount(val):
            if val >= 1000:
                return f"{val:,}đ"
            else:
                return f"{val:,}đ"
        
        if min_val and max_val:
            return f"{format_amount(min_val)} - {format_amount(max_val)}"
        elif min_val:
            return f"Từ {format_amount(min_val)}"
        else:
            return f"Đến {format_amount(max_val)}"


# Test function
def test_with_points():
    """Test the enhanced RAG with point deduction"""
    rag = TrafficLawRAGWithPoints(r"D:\crawl_law\nd168_metadata_clean.json")
    
    test_cases = [
        "Chạy quá tốc độ 25km/h trên cao tốc mức phạt ra sao?",
        "Xe ô tô rẽ phải sai quy định gây tai nạn thì phạt như thế nào?",
        "Vượt đèn đỏ bị phạt bao nhiêu và trừ mấy điểm?",
        "Cán vạch kẻ đường giữa 2 làn xe có nguy hiểm không?"
    ]
    
    for query in test_cases:
        result = rag.retrieve(query)
        
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")
        
        if result["status"] == "success":
            primary = result["primary_chunk"]
            print(f"\n📜 Reference: {primary['reference']}")
            print(f"Penalty: {primary['penalty']['text'] if primary['penalty'] else 'N/A'}")
            print(
                f"Point Deduction: {primary['point_deduction']} điểm"
                if primary['point_deduction']
                else "Point Deduction: None"
            )
            print(
                f"License Suspension: {primary['license_suspension']['text']}"
                if primary['license_suspension']
                else "License Suspension: None"
            )
            print(f"Priority: {primary['priority']}")
            print(f"\n📝 Content: {primary['content'][:200]}...")
        else:
            print(f"❌ {result['message']}")


if __name__ == "__main__":
    test_with_points()
