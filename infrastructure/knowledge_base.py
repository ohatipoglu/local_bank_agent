import os
import json
import logging
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

class KnowledgeBase:
    """
    Manages vector indexing and retrieval for banking FAQs.
    Uses 'nezahatkorkmaz/turkce-embedding-bge-m3' model.
    """

    def __init__(
        self,
        logger=None,
        persist_directory=None,
        kb_json_path=None,
        dict_json_path: str | None = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.persist_directory = persist_directory or "./data/chromadb"
        self.kb_json_path = kb_json_path or "./data/bank_kb.json"

        # Determine dictionary path to prevent test pollution
        if kb_json_path is not None and dict_json_path is None:
            self.dict_json_path = None
        else:
            self.dict_json_path = dict_json_path or "./data/banking_dictionary.json"
        
        # 1. Hardware-optimized device selection (CPU or XPU, no CUDA)
        self.device = "cpu"
        try:
            import torch
            if hasattr(torch, "xpu") and torch.xpu.is_available():
                self.device = "xpu"
                self.logger.info("Intel Arc GPU (XPU) algılandı. Embedding modeli XPU üzerinde çalışacak.")
            else:
                self.logger.info("Intel Extension for PyTorch (IPEX) veya XPU bulunamadı. CPU kullanılacak.")
        except Exception as e:
            self.logger.warning(f"Cihaz denetimi sırasında hata oluştu, CPU kullanılacak: {e}")
            
        # 2. Initialize Turkish BGE-M3 embedding model
        self.logger.info("nezahatkorkmaz/turkce-embedding-bge-m3 modeli yükleniyor...")
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name="nezahatkorkmaz/turkce-embedding-bge-m3",
                model_kwargs={"device": self.device},
                encode_kwargs={"normalize_embeddings": True}
            )
            self.logger.info("Embedding modeli başarıyla yüklendi.")
        except Exception as e:
            self.logger.error(f"Embedding modeli yüklenemedi: {e}")
            raise e
        
        # 3. Initialize ChromaDB
        try:
            self.db = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        except Exception as e:
            self.logger.error(f"ChromaDB başlatılamadı: {e}")
            raise e
        
        # 4. Populate knowledge base if empty
        self._populate_if_empty()
        
    def _populate_if_empty(self):
        try:
            count = self.db._collection.count()
            self.logger.info(f"Vektör veri tabanında {count} adet döküman bulunuyor.")
            if count == 0:
                self.logger.info("Vektör veri tabanı boş. Veriler yükleniyor...")
                self.load_and_index_documents()
        except Exception as e:
            self.logger.error(f"Vektör veri tabanı kontrol/indeksleme hatası: {e}")
            
    def load_and_index_documents(self):
        documents = []

        # 1. Load FAQ data
        if self.kb_json_path and os.path.exists(self.kb_json_path):
            try:
                with open(self.kb_json_path, "r", encoding="utf-8") as f:
                    kb_data = json.load(f)
                for entry in kb_data:
                    q = entry.get("question", "")
                    a = entry.get("answer", "")
                    content = f"Soru: {q}\nCevap: {a}"
                    documents.append(Document(page_content=content, metadata={"source": "bank_kb.json"}))
            except Exception as e:
                self.logger.error(f"Bilgi bankası yükleme hatası: {e}")
        else:
            self.logger.warning(f"Bilgi bankası dosyası bulunamadı veya belirtilmedi: {self.kb_json_path}")

        # 2. Load banking dictionary data
        if self.dict_json_path and os.path.exists(self.dict_json_path):
            try:
                with open(self.dict_json_path, "r", encoding="utf-8") as f:
                    dict_data = json.load(f)
                for entry in dict_data:
                    term = entry.get("term", "")
                    definition = entry.get("definition", "")
                    content = f"Terim: {term}\nAçıklama: {definition}"
                    documents.append(Document(page_content=content, metadata={"source": "banking_dictionary.json"}))
                self.logger.info(f"Banka sözlüğünden {len(dict_data)} adet terim eklendi.")
            except Exception as e:
                self.logger.error(f"Banka sözlüğü yükleme hatası: {e}")
        else:
            self.logger.info("Banka sözlüğü dosyası belirtilmedi veya bulunamadı, sözlük indekslenmeyecek.")

        if not documents:
            self.logger.error("Vektörleştirilecek döküman bulunamadı.")
            return

        try:
            # Chunking strategy (600 chunk size, 100 overlap)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=600,
                chunk_overlap=100,
                separators=["\n\n", "\n", " ", ""]
            )
            split_docs = text_splitter.split_documents(documents)
            
            self.logger.info(f"{len(split_docs)} adet parça (chunk) vektörleştiriliyor...")
            self.db.add_documents(split_docs)
            self.logger.info("Vektörleştirme ve indeksleme tamamlandı.")
        except Exception as e:
            self.logger.error(f"Bilgi bankası yükleme/indeksleme hatası: {e}")
            
    def get_retriever(self):
        return self.db.as_retriever(search_kwargs={"k": 3})
