import chromadb
from chromadb.config import Settings
import os
import uuid
from datetime import datetime

class VectorMemory:
    def __init__(self):
        self.client = chromadb.HttpClient(host='localhost', port=8000)
        self.collection = self.client.get_or_create_collection(name="quantum_memory")
        print(f"🧠 Memoria Connessa. Ricordi totali: {self.collection.count()}")

    def save(self, user_input, ai_response):
        """Salva solo se c'è sostanza"""
        # FILTRO 1: Ignora messaggi troppo brevi o inutili
        if len(user_input.strip()) < 5:
            return # Non salvare "ok", "ciao", "si"
            
        text_to_save = f"Utente: {user_input}\nQuantum: {ai_response}"
        mem_id = str(uuid.uuid4())
        now = datetime.now()
        
        self.collection.add(
            documents=[text_to_save],
            metadatas=[{
                "timestamp": now.timestamp(),
                "date_iso": now.strftime("%Y-%m-%d %H:%M:%S"),
                "type": "conversation"
            }],
            ids=[mem_id]
        )

    def search(self, query, n_results=5, threshold=1.5):
        """
        Recupera ricordi con filtro di qualità (Threshold).
        In ChromaDB, 'distance' più bassa = maggiore somiglianza.
        Una distanza > 1.5 solitamente è rumore.
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results['documents'] or not results['documents'][0]:
                return "Nessuna memoria disponibile."

            context_string = ""
            found_useful_memory = False
            
            # Uniamo documenti, metadati e distanze
            memories = zip(
                results['documents'][0], 
                results['metadatas'][0], 
                results['distances'][0]
            )
            
            for doc, meta, dist in memories:
                # FILTRO 2: Ignora ricordi troppo diversi (Soglia)
                if dist > threshold:
                    continue
                
                found_useful_memory = True
                date_str = meta.get('date_iso', 'Data Sconosciuta')
                context_string += f"--- [MEMORIA DEL {date_str} | Rilevanza: {100-int(dist*50)}%] ---\n{doc}\n\n"
            
            if not found_useful_memory:
                return "Nessuna memoria pertinente trovata (Soglia non superata)."
                
            return context_string

        except Exception as e:
            return f"Errore recupero memoria: {e}"
