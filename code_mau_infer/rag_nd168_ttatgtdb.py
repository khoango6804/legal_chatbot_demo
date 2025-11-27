"""
RAG Pipeline for ND168 + Luật TTATGTĐB (2 laws)
Based on rag_pipeline_with_points_base.py but simplified for 2 laws only
"""

from rag_pipeline_with_points_base import TrafficLawRAGWithPoints

class TrafficLawRAG2Laws(TrafficLawRAGWithPoints):
    """RAG Pipeline for ND168 + Luật TTATGTĐB only"""
    
    def __init__(self, merged_data_path: str = None):
        """
        Initialize with merged data file
        
        Args:
            merged_data_path: Path to merged ND168+TTATGTĐB JSON file
                             (default: rag_2_luat/nd168_ttatgtdb_merged.json)
        """
        if merged_data_path is None:
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            merged_data_path = os.path.join(current_dir, 'nd168_ttatgtdb_merged_khoan.json')
        
        print(f"Loading merged data from: {merged_data_path}")
        
        # Initialize parent class with merged data
        super().__init__(data_path=merged_data_path)
        
        # Store path for reference
        self.merged_data_path = merged_data_path
        
        print(f"Initialized with {len(self.chunks)} chunks from 2 laws\n")
    
    def retrieve(self, query: str, verbose: bool = False) -> dict:
        """
        Retrieve with automatic query type detection
        
        Args:
            query: User's question
            verbose: Whether to print debug info
            
        Returns:
            Retrieved results (penalty or concept)
        """
        query_lower = query.lower()
        
        # Concept query indicators
        concept_indicators = [
            'là gì', 'định nghĩa', 'khái niệm', 'nghĩa là', 'ý nghĩa',
            'giải thích', 'phạm vi', 'đối tượng áp dụng', 'hiểu như thế nào',
            'được hiểu là', 'bao gồm những', 'gồm những gì'
        ]
        
        # Rule/regulation query indicators
        rule_indicators = [
            'có phải', 'phải không', 'có cần', 'cần không', 'có được', 
            'được không', 'có bắt buộc', 'bắt buộc không', 'quy định',
            'có quy định', 'luật có', 'pháp luật có', 'phải đi', 'phải chạy',
            'phải tuân thủ', 'phải chấp hành', 'được phép', 'không được phép',
            'phải làm', 'cần làm', 'bên nào', 'làn nào', 'như thế nào',
            'có mấy', 'mấy màu', 'có bao nhiêu',
            'trường hợp nào', 'những trường hợp', 'trong trường hợp nào',
            'khi nào phải', 'khi nào cần', 'tình huống nào'
        ]
        
        is_concept_query = any(indicator in query_lower for indicator in concept_indicators)
        # Exclude penalty keywords from rule queries, and exclude case-listing queries
        penalty_keywords = ['bị phạt', 'phạt bao nhiêu', 'mức phạt', 'tiền phạt']
        is_rule_query = (any(indicator in query_lower for indicator in rule_indicators) 
                        and not any(kw in query_lower for kw in penalty_keywords))
        
        if verbose:
            if is_concept_query:
                print(f"\nQuery type: CONCEPT")
            elif is_rule_query:
                print(f"\nQuery type: RULE")
            else:
                print(f"\nQuery type: PENALTY")
        
        # For concept/rule queries, use dedicated retrieval
        if is_concept_query or is_rule_query:
            return self._retrieve_concept(query, verbose, is_rule_query)
        
        # For penalty queries, use base class retrieve
        return super().retrieve(query)
    
    def _retrieve_concept(self, query: str, verbose: bool = False, is_rule_query: bool = False) -> dict:
        """
        Retrieve concept definitions or rules from law articles
        
        Args:
            query: User's question
            verbose: Whether to print debug info
            is_rule_query: Whether this is a rule query (vs concept definition)
            
        Returns:
            Dictionary with retrieved information
        """
        query_lower = query.lower()
        
        # Extract search terms
        concept_query = query_lower
        for indicator in ['là gì', 'định nghĩa', 'khái niệm', 'giải thích', 'có phải', 'phải không']:
            if indicator in concept_query:
                concept_query = concept_query.replace(indicator, '').strip('? ')
        
        if verbose:
            print(f"   Concept search term: '{concept_query}'")
        
        # Extract key terms
        key_terms = []
        for word in concept_query.split():
            if len(word) > 3 and word not in ['phải', 'không', 'được', 'có', 'cần', 'bắt', 'buộc']:
                key_terms.append(word)
        
        # Score all chunks
        matched_chunks = []
        for chunk in self.chunks:
            chunk_text = chunk.content.lower()
            score = 0
            
            # Count key term matches
            term_matches = sum(1 for term in key_terms if term in chunk_text)
            if term_matches > 0:
                score += term_matches * 50
            
            # Exact term match bonus
            if concept_query in chunk_text:
                score += 100
            
            # Strong boost for definition pattern "X là" in queries
            # Check if this chunk defines the exact term being asked about
            # e.g., "Dừng xe là trạng thái..." for query "dừng xe là gì?"
            definition_pattern = f"{concept_query} là"
            if definition_pattern in chunk_text:
                score += 500
                # Extra boost if it's a concept record type (not rule query)
                if hasattr(chunk, 'record_type') and chunk.record_type == 'concept' and not is_rule_query:
                    score += 200
            
            # Special boost for specific rules
            if 'thắt dây' in chunk_text or 'dây đai an toàn' in chunk_text:
                if hasattr(chunk, 'record_type') and chunk.record_type == 'rule':
                    score += 200
                    if hasattr(chunk, 'article') and chunk.article == 10:
                        score += 100
            
            # Boost for traffic direction rules (bên phải, làn đường)
            if ('bên phải' in query_lower or 'bên nào' in query_lower or 'làn đường' in query_lower):
                if 'bên phải' in chunk_text or 'chiều đi' in chunk_text or 'làn đường' in chunk_text:
                    score += 200
                    # Extra boost for Điều 10 khoản 1 (general traffic rules)
                    if hasattr(chunk, 'article') and chunk.article == 10:
                        score += 150
            
            # Boost for traffic light questions (đèn giao thông, tín hiệu đèn)
            if ('đèn giao thông' in query_lower or 'đèn tín hiệu' in query_lower or 
                'mấy màu' in query_lower or 'màu sắc' in query_lower):
                # Strong match for content with color names
                if 'tín hiệu đèn' in chunk_text and ('màu xanh' in chunk_text or 'màu vàng' in chunk_text or 'màu đỏ' in chunk_text):
                    score += 400
                    # Extra boost for Điều 11 khoản 4 (traffic light regulations)
                    if hasattr(chunk, 'article') and chunk.article == 11 and hasattr(chunk, 'clause') and chunk.clause == 4:
                        score += 300
                # Weaker match for just mentioning traffic lights
                elif 'đèn giao thông' in chunk_text or 'tín hiệu đèn' in chunk_text:
                    score += 100
            
            # Boost for case/situation queries (trường hợp nào, tình huống nào)
            if ('trường hợp nào' in query_lower or 'những trường hợp' in query_lower or 
                'trong trường hợp nào' in query_lower or 'tình huống nào' in query_lower):
                # Strong boost if this is from law source (not penalty decree)
                if hasattr(chunk, 'source') and chunk.source == 'luat_ttatgtdb':
                    score += 200
                    # Extra boost for Điều 12 khoản 3 (safety observation requirements)
                    if hasattr(chunk, 'article') and chunk.article == 12 and hasattr(chunk, 'clause') and chunk.clause == 3:
                        score += 500
                        # Even more if query mentions "quan sát" or "giảm tốc độ"
                        if 'quan sát' in query_lower or 'giảm tốc độ' in query_lower:
                            score += 300
            
            # Scoring strategy based on query type
            if is_rule_query:
                # For rule queries: PENALIZE definitions, BOOST rules
                if hasattr(chunk, 'record_type'):
                    if chunk.record_type == 'concept':
                        score -= 300  # Heavy penalty for definitions
                    elif chunk.record_type == 'rule' and term_matches >= 2:
                        score += 300  # Big bonus for rules with matches
            else:
                # For concept queries: BOOST definitions
                if hasattr(chunk, 'record_type') and chunk.record_type == 'concept':
                    score += 200
            
            # Bonus for law sources (TTATGTĐB or specific articles)
            if hasattr(chunk, 'source'):
                law_sources = ['luat_ttatgtdb', 'luat_duong_bo']
                if chunk.source in law_sources:
                    score += 150
                    
                    # Extra bonus for Điều 2, 3 (definitions usually here)
                    if hasattr(chunk, 'article') and chunk.article in [2, 3] and not is_rule_query:
                        score += 100
            
            if score > 0:
                matched_chunks.append({
                    'chunk': chunk,
                    'score': score,
                    'term_matches': term_matches
                })
        
        if not matched_chunks:
            return {
                "status": "error",
                "message": "Không tìm thấy định nghĩa hoặc giải thích liên quan",
                "query": query
            }
        
        # Sort by score
        matched_chunks.sort(key=lambda x: x['score'], reverse=True)
        
        if verbose:
            print(f"   Found {len(matched_chunks)} concept matches")
            for i, m in enumerate(matched_chunks[:5]):
                chunk = m['chunk']
                source = getattr(chunk, 'source', 'nd168')
                article = getattr(chunk, 'article', '?')
                record_type = getattr(chunk, 'record_type', '?')
                print(f"     - {source} Điều {article} (score={m['score']}, type={record_type})")
        
        # Get top match
        best_match = matched_chunks[0]['chunk']
        
        # Format reference
        source_name = {
            'luat_ttatgtdb': 'Luật TTATGTĐB 2024',
            'nd168': 'Nghị định 168/2024/NĐ-CP'
        }.get(best_match.source, 'Văn bản')
        
        reference = f"{source_name} - Điều {best_match.article}"
        if best_match.khoan:
            reference += f" khoản {best_match.khoan}"
        if best_match.diem:
            reference += f" điểm {best_match.diem}"
        
        return {
            "status": "success",
            "query_type": "concept",
            "primary_chunk": {
                "reference": reference,
                "content": best_match.content,
                "source": best_match.source,
                "article": best_match.article,
                "khoan": best_match.khoan,
                "diem": best_match.diem,
                "tags": list(best_match.tags),
                "record_type": getattr(best_match, 'record_type', 'rule'),
                "is_escalation": best_match.is_escalation,
                "priority": best_match.priority
            }
        }


def main():
    """Test the 2-law RAG pipeline"""
    
    print("="*80)
    print("RAG PIPELINE FOR ND168 + LUẬT TTATGTĐB")
    print("="*80)
    print()
    
    # Initialize with merged data
    rag = TrafficLawRAG2Laws()
    
    # Test queries
    test_queries = [
        "Xe ô tô vượt đèn đỏ gây tai nạn bị phạt bao nhiêu?",
        "Người tham gia giao thông là gì?",
        "Xe máy chạy quá tốc độ 20km/h bị phạt sao?",
        "Người ngồi ghế sau có phải thắt dây an toàn không?"
    ]
    
    print("\nTesting with sample queries...\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{len(test_queries)}")
        print(f"{'='*80}")
        print(f"Query: {query}")
        
        result = rag.retrieve(query, verbose=True)
        
        if result["status"] == "success":
            primary = result["primary_chunk"]
            print(f"\n✓ Retrieved: {primary['reference']}")
            print(f"  Content: {primary['content'][:200]}...")
            if result.get("query_type") == "concept":
                print(f"  Type: CONCEPT/RULE")
            else:
                if primary.get('penalty'):
                    print(f"  Penalty: {primary['penalty']['text']}")
                if primary.get('point_deduction'):
                    print(f"  Points: {primary['point_deduction']} điểm")
        else:
            print(f"\n✗ Error: {result['message']}")
    
    print(f"\n{'='*80}")
    print("Testing complete!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
