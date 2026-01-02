import chromadb
import uuid
import time
import os

class VectorMemory:
    def __init__(self):
        print("🧠 Inizializzazione Memoria Quantistica...")
        # Connessione al container ChromaDB
        # Usa host.docker.internal se su Mac/Windows, localhost se in network_mode: host
        self.client = chromadb.HttpClient(host='localhost', port=8000)
        
        # Creiamo o recuperiamo la collezione "quantum_knowledge"
        self.collection = self.client.get_or_create_collection(name="quantum_knowledge")
        print(f"📚 Memoria connessa. Ricordi salvati: {self.collection.count()}")

    def save(self, user_text, ai_text):
        """Salva lo scambio User/AI nella memoria vettoriale"""
        interaction = f"Domanda: {user_text}\nRisposta: {ai_text}"
        
        self.collection.add(
            documents=[interaction],
            metadatas=[{"timestamp": time.time(), "type": "chat"}],
            ids=[str(uuid.uuid4())]
        )

    def search(self, query, n_results=1):
        """Cerca ricordi pertinenti alla query"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if results['documents'] and results['documents'][0]:
                return results['documents'][0][0] # Ritorna il testo del primo risultato
            return "Nessun dato rilevante trovato."
        except Exception as e:
            return f"Errore memoria: {e}"
