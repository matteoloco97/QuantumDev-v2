import requests
import json
import time
import os
import sys

# CONFIGURAZIONE
API_URL = "http://localhost:8001/chat/god-mode"
PROJECT_FILE = "roadmap.json"

def print_system(text):
    print(f"\033[96m[SYSTEM] {text}\033[0m")

def print_ai(text):
    print(f"\033[92m[QUANTUM] {text}\033[0m")

def init_project():
    """Se non esiste un progetto, ne chiediamo uno all'utente."""
    if not os.path.exists(PROJECT_FILE):
        print_system("Nessun progetto attivo.")
        goal = input("Cosa vuoi costruire oggi? > ")
        
        initial_state = {
            "goal": goal,
            "status": "PLANNING", # PLANNING -> WORKING -> TESTING -> DONE
            "tasks": [],
            "current_task_index": 0,
            "completed_files": []
        }
        with open(PROJECT_FILE, "w") as f:
            json.dump(initial_state, f, indent=4)
        return initial_state
    
    with open(PROJECT_FILE, "r") as f:
        return json.load(f)

def update_project(state):
    with open(PROJECT_FILE, "w") as f:
        json.dump(state, f, indent=4)

def call_quantum(prompt):
    payload = {"message": prompt, "history": []}
    try:
        resp = requests.post(API_URL, json=payload, timeout=300)
        return resp.json().get("response", "")
    except Exception as e:
        return f"ERRORE API: {e}"

def main():
    print_system("QUANTUM ORCHESTRATOR V1.0 - AVVIATO")
    state = init_project()

    while state["status"] != "DONE":
        print("\n" + "="*50)
        print(f" STATO PROGETTO: {state['status']}")
        print(f" OBIETTIVO: {state['goal']}")
        print("="*50)

        # FASE 1: PIANIFICAZIONE
        if state["status"] == "PLANNING":
            print_system("Chiedo all'AI di creare la lista dei task...")
            prompt = f"""
            Agisci come Tech Lead. OBIETTIVO: {state['goal']}
            
            Analizza l'obiettivo e crea una lista di task tecnici SEQUENZIALI per realizzarlo.
            Ogni task deve essere la creazione di un singolo file o modulo.
            
            RISPONDI SOLO CON UN JSON PURO in questo formato (senza markdown):
            {{
                "tasks": ["Creare file requirements.txt", "Scrivere scraper.py", "Scrivere main.py", "Testare tutto"]
            }}
            """
            response = call_quantum(prompt)
            # Pulizia brutale del JSON (l'AI a volte mette ```json ... ```)
            clean_json = response.replace("```json", "").replace("```", "").strip()
            
            try:
                data = json.loads(clean_json)
                state["tasks"] = data["tasks"]
                state["status"] = "WORKING"
                update_project(state)
                print_system(f"Piano approvato: {len(state['tasks'])} step.")
            except:
                print_system("Errore nel parsing del piano. Riprovo...")
                continue

        # FASE 2: ESECUZIONE (WORKING)
        elif state["status"] == "WORKING":
            if state["current_task_index"] >= len(state["tasks"]):
                state["status"] = "TESTING"
                update_project(state)
                continue

            current_task = state["tasks"][state["current_task_index"]]
            print_system(f"Esecuzione Task {state['current_task_index']+1}/{len(state['tasks'])}: {current_task}")
            
            prompt = f"""
            SEI IN MODALITÀ "OPERAIO". NON CHIACCHIERARE.
            PROGETTO: {state['goal']}
            TASK CORRENTE: {current_task}
            
            ISTRUZIONI:
            1. Esegui il task (es. scrivi il codice usando [TOOL: write_file]).
            2. Se devi installare librerie, dimmelo.
            3. Quando hai finito e salvato il file, rispondi con la parola chiave: "TASK_COMPLETATO".
            """
            
            response = call_quantum(prompt)
            print_ai(response)

            # Controllo manuale o automatico?
            # Qui applichiamo la tua filosofia: L'AI lavora, tu controlli solo se serve.
            if "TASK_COMPLETATO" in response:
                print_system("Task segnato come fatto.")
                state["current_task_index"] += 1
                update_project(state)
            else:
                print_system("Il task sembra incompleto. Riprovo o vuoi intervenire?")
                x = input("[ENTER] per continuare, [M] per messaggio manuale: ")
                if x.lower() == "m":
                    man = input("Tu > ")
                    call_quantum(man) # Invio manuale one-shot

        # FASE 3: CHIUSURA
        elif state["status"] == "TESTING":
            print_system("Tutti i task sono finiti. Vuoi eseguire un test finale?")
            cmd = input("Comando da lanciare (es. python main.py) o 'skip': ")
            if cmd != "skip":
                call_quantum(f"Esegui questo test finale usando [TOOL: terminal_run]: {cmd}")
            
            state["status"] = "DONE"
            update_project(state)
            print_system("PROGETTO COMPLETATO. TI SEI GUADAGNATO IL RIPOSO.")
            break

        time.sleep(2) # Respiro tra i cicli

if __name__ == "__main__":
    main()
