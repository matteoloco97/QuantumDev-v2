import asyncio
from duckduckgo_search import DDGS

class Toolbox:
    @staticmethod
    async def search_web(query: str, max_results: int = 5) -> str:
        print(f"🔎 Cerca: {query}...")
        try:
            results = await asyncio.to_thread(lambda: list(DDGS().text(query, max_results=max_results)))
            if not results: return "Nessun risultato."
            return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
        except Exception as e: return f"Errore ricerca: {e}"

    @staticmethod
    async def execute_python(code: str) -> str:
        print(f"💻 Esegue codice...")
        clean = code.replace("```python", "").replace("```", "").strip()
        if any(bad in clean for bad in ['os.system', 'subprocess']): return "⛔ Vietato."
        try:
            proc = await asyncio.create_subprocess_exec("python3", "-c", clean, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out, err = await proc.communicate()
            return f"Out: {out.decode()}\nErr: {err.decode()}"
        except Exception as e: return f"Errore: {e}"

TOOLS_SCHEMA = [
    {"type": "function", "function": {"name": "search_web", "description": "Cerca online", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "execute_python", "description": "Esegue Python", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}}
]
