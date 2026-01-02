import chromadb
from chromadb.config import Settings
import os
import uuid
from datetime import datetime

class VectorMemory:
    def __init__(self):
        # Connessione persistente
        self.client = chromadb.HttpClient(host='localhost', port=8000)
        self.collection = self.client.get_or_create_collection(name="quantum_memory")
        print(f"🧠 Memoria V4 Attiva. Ricordi: {self.collection.count()}")

    def save(self, user_input, fact_extracted):
        """
        Salva un concetto distillato (fact_extracted) collegandolo all'input originale.
        """
        if not fact_extracted or len(fact_extracted) < 5:
            return

        mem_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Salviamo il "Fatto" come documento principale
        text_to_save = f"FATTO: {fact_extracted}\nCONTESTO ORIGINALE: {user_input}"
        
        self.collection.add(
            documents=[text_to_save],
            metadatas=[{
                "timestamp": now.timestamp(),
                "date_iso": now.strftime("%Y-%m-%d %H:%M:%S"),
                "type": "fact"
            }],
            ids=[mem_id]
        )
        print(f"💾 [DB] Ricordo cristallizzato: {fact_extracted[:50]}...")

    def search(self, query, n_results=5, threshold=1.4):
        """
        Recupera ricordi filtrando quelli poco pertinenti (Threshold).
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results['documents'] or not results['documents'][0]:
                return "Nessun dato storico rilevante."

            context_string = ""
            valid_memories = 0
            
            memories = zip(
                results['documents'][0], 
                results['metadatas'][0], 
                results['distances'][0]
            )
            
            for doc, meta, dist in memories:
                if dist > threshold:
                    continue
                
                valid_memories += 1
                date_str = meta.get('date_iso', 'Data Sconosciuta')
                context_string += f"--- [MEMORIA DEL {date_str}] ---\n{doc}\n\n"
            
            if valid_memories == 0:
                return "Nessun dato storico pertinente (Filtro Qualità)."
                
            return context_string

        except Exception as e:
            return f"Errore Memoria: {e}"
