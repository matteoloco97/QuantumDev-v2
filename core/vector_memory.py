import os
import logging
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Carica variabili d'ambiente (se presenti)
load_dotenv()

# Configurazione Base
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
CHROMA_COLLECTION = "quantum_memory"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Variabili globali per il singleton
_chroma_client = None
_collection = None
_embedding_function = None

def _get_embedding_function():
    """Inizializza il modello di embedding (SentenceTransformer)."""
    global _embedding_function
    if _embedding_function is None:
        try:
            from chromadb.utils import embedding_functions
            _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )
        except Exception as e:
            print(f"⚠️ Errore init embedding: {e}. Uso default.")
            import chromadb
            _embedding_function = chromadb.utils.embedding_functions.DefaultEmbeddingFunction()
    return _embedding_function

def _get_collection():
    """Recupera o crea la collezione ChromaDB."""
    global _chroma_client, _collection
    
    if _collection is None:
        try:
            import chromadb
            
            # Assicura che la directory esista
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            
            # Inizializza Client Persistente
            if _chroma_client is None:
                _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            
            # Recupera/Crea collezione
            _collection = _chroma_client.get_or_create_collection(
                name=CHROMA_COLLECTION,
                embedding_function=_get_embedding_function(),
                metadata={"description": "Quantum v2 Long Term Memory"}
            )
            print(f"🧠 Memoria connessa: {CHROMA_COLLECTION}")
        except Exception as e:
            print(f"❌ Errore critico ChromaDB: {e}")
            raise e
            
    return _collection

def add_document(session_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Salva un pensiero o un'informazione nella memoria vettoriale."""
    if not text or not text.strip():
        return False
    
    try:
        col = _get_collection()
        
        # Genera ID univoco basato su contenuto e tempo
        doc_id = hashlib.sha256(f"{session_id}:{text[:50]}:{time.time()}".encode()).hexdigest()[:16]
        
        # Prepara metadati sicuri
        safe_meta = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "source": "user_interaction"
        }
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    safe_meta[k] = v

        col.add(
            documents=[text],
            metadatas=[safe_meta],
            ids=[doc_id]
        )
        return True
    except Exception as e:
        print(f"⚠️ Errore salvataggio memoria: {e}")
        return False

def query_documents(session_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Cerca ricordi rilevanti per similarità semantica."""
    if not query or not query.strip():
        return []
    
    try:
        col = _get_collection()
        
        results = col.query(
            query_texts=[query],
            n_results=top_k,
            # Se vuoi filtrare per sessione decommenta sotto:
            # where={"session_id": session_id} 
        )
        
        docs = []
        if results and results.get("documents"):
            for i, text in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                dist = results["distances"][0][i] if results.get("distances") else 0.0
                docs.append({
                    "text": text,
                    "metadata": meta,
                    "distance": dist
                })
        return docs
    except Exception as e:
        print(f"⚠️ Errore lettura memoria: {e}")
        return []
