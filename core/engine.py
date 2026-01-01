import os
import json
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
# Assumiamo che vector_memory sia presente (Step successivo)
from core.vector_memory import query_documents, add_document
from core.tools import Toolbox, TOOLS_SCHEMA

load_dotenv()

class QuantumEngine:
    def __init__(self):
        # CONFIGURAZIONE TUNNEL GPU
        self.client = AsyncOpenAI(
            base_url="http://localhost:5000/v1", # Punta al tunnel SSH
            api_key="sk-internal"
        )
        self.model = "model-placeholder" 
        print(f"🚀 QuantumEngine v2 avviato su GPU Locale (Tunnel :5000)")

    async def _get_memory_context(self, query: str) -> str:
        try:
            docs = query_documents(session_id="global", query=query, top_k=3)
            if not docs: return ""
            context_str = "\n".join([f"- {d['text']}" for d in docs])
            return f"\n🧠 MEMORIA:\n{context_str}\n"
        except Exception: return ""

    async def process(self, user_input: str) -> str:
        memory = await self._get_memory_context(user_input)
        messages = [
            {"role": "system", "content": f"Sei Quantum. Rispondi in modo diretto. Usa i tool solo se serve. {memory}"},
            {"role": "user", "content": user_input}
        ]

        try:
            # 1. Decisione (Tool vs Risposta)
            response = await self.client.chat.completions.create(
                model=self.model, messages=messages, tools=TOOLS_SCHEMA, tool_choice="auto", temperature=0.7
            )
            msg = response.choices[0].message

            # 2. Esecuzione Tool
            if msg.tool_calls:
                print(f"🛠️ Tool: {msg.tool_calls[0].function.name}")
                messages.append(msg)
                for tool in msg.tool_calls:
                    args = json.loads(tool.function.arguments)
                    res = "Err"
                    if tool.function.name == "search_web": res = await Toolbox.search_web(**args)
                    elif tool.function.name == "execute_python": res = await Toolbox.execute_python(**args)
                    messages.append({"role": "tool", "tool_call_id": tool.id, "name": tool.function.name, "content": str(res)})
                
                # 3. Sintesi Finale
                final = await self.client.chat.completions.create(model=self.model, messages=messages)
                answer = final.choices[0].message.content
            else:
                answer = msg.content

            # 4. Memoria
            if len(answer) > 50: add_document(session_id="global", text=f"Q: {user_input}\nA: {answer}")
            return answer
        except Exception as e:
            return f"❌ Errore LLM (Controlla il tunnel!): {e}"

if __name__ == "__main__":
    async def main():
        engine = QuantumEngine()
        try:
            # Check connessione all'avvio
            models = await engine.client.models.list()
            engine.model = models.data[0].id
            print(f"✅ Connesso a: {engine.model}")
        except: print("⚠️ Tunnel non rilevato sulla porta 5000.")
        
        while True:
            q = input("\nTu: ")
            if q in ["exit", "quit"]: break
            print(f"Quantum: {await engine.process(q)}")
    asyncio.run(main())
