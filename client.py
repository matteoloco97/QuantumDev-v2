import requests
import json
import sys
import time

# Configurazione
API_URL = "http://localhost:8001/chat/god-mode"

def type_writer(text):
    """Effetto macchina da scrivere per una UI più figa"""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.005)
    print("")

def main():
    print("\n" + "="*50)
    print("   QUANTUM v2.4 - GOD MODE INTERFACE")
    print("   API Connection: ACTIVE (Port 8001)")
    print("="*50 + "\n")

    history = []

    while True:
        try:
            user_input = input("\n[TU] > ")
            if user_input.lower() in ['exit', 'quit']:
                break

            # Prepariamo il payload
            payload = {
                "message": user_input,
                "history": history[-4:] # Mandiamo gli ultimi scambi per contesto
            }

            print(" quantum sta pensando...", end="\r")

            # Chiamata API
            start_time = time.time()
            try:
                response = requests.post(API_URL, json=payload, timeout=120)
                response.raise_for_status()
                data = response.json()
                
                elapsed = time.time() - start_time
                
                # Risposta AI
                print(f"\r[QUANTUM ({elapsed:.1f}s)] > ", end="")
                
                # Visualizza Risposta
                msg = data.get("response", "Errore nella risposta")
                tool = data.get("tool_used")
                
                if tool:
                    print(f"\033[93m[TOOL: {tool}]\033[0m") # Giallo se usa tool
                
                type_writer(msg)

                # Aggiorna storico locale (per la sessione corrente)
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": msg})

            except requests.exceptions.ConnectionError:
                print("\n❌ ERRORE: Il server API sembra spento. Controlla Docker.")
            except Exception as e:
                print(f"\n❌ ERRORE: {e}")

        except KeyboardInterrupt:
            print("\nDisconnessione...")
            break

if __name__ == "__main__":
    main()
