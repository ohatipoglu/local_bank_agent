import os
import shutil
import tempfile
import pytest
import json
from unittest.mock import MagicMock
from infrastructure.knowledge_base import KnowledgeBase

class TestKnowledgeBase:
    """Integration tests for KnowledgeBase vector indexing and retrieval."""

    @pytest.fixture
    def temp_kb_setup(self):
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        persist_dir = os.path.join(temp_dir, "chromadb")
        kb_file = os.path.join(temp_dir, "bank_kb.json")
        
        # Write dummy FAQ data
        dummy_data = [
            {
                "question": "FAST limiti nedir?",
                "answer": "FAST limiti günlük 100.000 TL'dir."
            },
            {
                "question": "EFT saatleri nedir?",
                "answer": "EFT saatleri iş günlerinde 09:00 ile 17:00 arasındadır."
            }
        ]
        with open(kb_file, "w", encoding="utf-8") as f:
            json.dump(dummy_data, f)
            
        yield persist_dir, kb_file
        
        # Cleanup
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
            
    def test_knowledge_base_indexing_and_retrieval(self, temp_kb_setup):
        """Test that KnowledgeBase correctly indexes documents and retrieves them semantically."""
        persist_dir, kb_file = temp_kb_setup
        
        logger = MagicMock()
        
        # Initialize knowledge base
        kb = KnowledgeBase(logger=logger, persist_directory=persist_dir, kb_json_path=kb_file)
        
        # Verify properties
        assert kb.device in ["cpu", "xpu"]
        assert kb.embeddings is not None
        assert kb.db is not None
        
        # Check document count
        count = kb.db._collection.count()
        assert count == 2
        
        # Test semantic search
        retriever = kb.get_retriever()
        docs = retriever.invoke("FAST limiti")
        assert len(docs) > 0
        
        contents = [doc.page_content for doc in docs]
        assert any("FAST limiti" in c for c in contents)

    def test_knowledge_base_with_dictionary(self, temp_kb_setup):
        """Test that KnowledgeBase correctly indexes both FAQ and banking dictionary when provided."""
        persist_dir, kb_file = temp_kb_setup
        
        # Create a temp banking dictionary file
        temp_dir = os.path.dirname(kb_file)
        dict_file = os.path.join(temp_dir, "banking_dictionary.json")
        dummy_dict = [
            {
                "term": "Valör",
                "definition": "İşlemin gerçekleştiği tarihtir."
            },
            {
                "term": "Temerrüt",
                "definition": "Borcun zamanında ödenmemesidir."
            }
        ]
        with open(dict_file, "w", encoding="utf-8") as f:
            json.dump(dummy_dict, f)
            
        logger = MagicMock()
        
        # Initialize knowledge base with both FAQ and dictionary
        kb = KnowledgeBase(
            logger=logger,
            persist_directory=persist_dir,
            kb_json_path=kb_file,
            dict_json_path=dict_file
        )
        
        # Verify document count (2 FAQ entries + 2 Dictionary entries = 4 total)
        count = kb.db._collection.count()
        assert count == 4
        
        # Test semantic search on dictionary term
        retriever = kb.get_retriever()
        docs = retriever.invoke("Valör")
        assert len(docs) > 0
        
        contents = [doc.page_content for doc in docs]
        assert any("Valör" in c or "tarihtir" in c for c in contents)
