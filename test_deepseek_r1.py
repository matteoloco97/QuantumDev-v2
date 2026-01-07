"""
🧪 Test diagnostico per DeepSeek-R1
Verifica il comportamento del model con <think> tags e JSON generation
"""
import requests
import re
import json
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

LLM_URL = "http://localhost:5000/v1/chat/completions"
MODEL = "DeepSeek-R1-Distill-Qwen-32B-abliterated-Q6_K.gguf"

def clean_think_tags(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def extract_json(text):
    clean = clean_think_tags(text)
    clean = clean.replace("```json", "").replace("```", "").strip()
    match = re.search(r'\[.*?\]', clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            return None
    return None

def test_json_generation():
    console.print(Panel("[bold cyan]TEST 1: JSON Generation[/bold cyan]", border_style="cyan"))
    
    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": """
            Genera un array JSON con 4 file Python necessari per un web scraper che salva dati.
            
            FORMATO RICHIESTO:
            1. Ragiona dentro <think>...</think>
            2. Dopo </think>, scrivi SOLO l'array JSON: ["file1.py", "file2.py", ...]
            
            NON aggiungere altro testo dopo il JSON.
            """
        }],
        "temperature": 0.05,
        "max_tokens": 1000
    }
    
    console.print("[yellow]⏳ Chiamata a LLM...[/yellow]")
    resp = requests.post(LLM_URL, json=payload, timeout=30)
    content = resp.json()['choices'][0]['message']['content']
    
    console.print(Panel(content, title="[bold]RAW OUTPUT[/bold]", border_style="blue"))
    
    # Test parsing
    clean = clean_think_tags(content)
    console.print(Panel(clean, title="[bold]AFTER <think> REMOVAL[/bold]", border_style="green"))
    
    parsed = extract_json(content)
    if parsed:
        console.print(f"\n[bold green]✅ SUCCESS: JSON Parsed correctly[/bold green]")
        console.print(Syntax(json.dumps(parsed, indent=2), "json", theme="monokai"))
    else:
        console.print(f"\n[bold red]❌ FAIL: Could not parse JSON[/bold red]")
    
    return parsed is not None

def test_code_generation():
    console.print(Panel("[bold cyan]TEST 2: Code Generation[/bold cyan]", border_style="cyan"))
    
    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": """
            Scrivi una funzione Python che legge un file JSON.
            
            FORMATO:
            1. Ragiona dentro <think>
            2. Dopo </think>, scrivi SOLO il codice dentro ```python ... ```
            """
        }],
        "temperature": 0.2,
        "max_tokens": 800
    }
    
    console.print("[yellow]⏳ Chiamata a LLM...[/yellow]")
    resp = requests.post(LLM_URL, json=payload, timeout=30)
    content = resp.json()['choices'][0]['message']['content']
    
    console.print(Panel(content[:500] + "...", title="[bold]RAW OUTPUT (truncated)[/bold]", border_style="blue"))
    
    # Extract code
    clean = clean_think_tags(content)
    match = re.search(r'```(?:python)?\s*(.*?)```', clean, re.DOTALL)
    
    if match:
        code = match.group(1).strip()
        console.print(f"\n[bold green]✅ SUCCESS: Code extracted[/bold green]")
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
        return True
    else:
        console.print(f"\n[bold red]❌ FAIL: Could not extract code[/bold red]")
        return False

def test_reasoning_quality():
    console.print(Panel("[bold cyan]TEST 3: Reasoning Quality Check[/bold cyan]", border_style="cyan"))
    
    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": "Spiega in 2 frasi cosa fa un web scraper. Usa <think> per ragionare, poi rispondi."
        }],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    console.print("[yellow]⏳ Chiamata a LLM...[/yellow]")
    resp = requests.post(LLM_URL, json=payload, timeout=20)
    content = resp.json()['choices'][0]['message']['content']
    
    has_think = "<think>" in content.lower()
    clean = clean_think_tags(content)
    
    console.print(Panel(content, title="[bold]RAW OUTPUT[/bold]", border_style="blue"))
    console.print(Panel(clean, title="[bold]CLEAN OUTPUT (user-facing)[/bold]", border_style="green"))
    
    if has_think and len(clean) > 20:
        console.print(f"\n[bold green]✅ SUCCESS: Model uses <think> correctly[/bold green]")
        return True
    else:
        console.print(f"\n[bold red]❌ FAIL: No <think> tags or empty response[/bold red]")
        return False

def main():
    console.print(Panel(
        "[bold white]DeepSeek-R1 Diagnostic Test Suite[/bold white]\nVerifying model behavior with reasoning tags",
        title="[bold magenta]🧪 QUANTUM TEST LAB[/bold magenta]",
        border_style="magenta"
    ))
    
    results = {
        "JSON Generation": test_json_generation(),
        "Code Generation": test_code_generation(),
        "Reasoning Quality": test_reasoning_quality()
    }
    
    console.print("\n" + "="*60)
    console.print("[bold]TEST SUMMARY:[/bold]")
    for test_name, passed in results.items():
        status = "[green]✅ PASS[/green]" if passed else "[red]❌ FAIL[/red]"
        console.print(f"{test_name}: {status}")
    
    total = sum(results.values())
    console.print(f"\n[bold]Score: {total}/3[/bold]")
    
    if total == 3:
        console.print("[bold green]🎉 ALL TESTS PASSED! DeepSeek-R1 working correctly.[/bold green]")
    else:
        console.print("[bold yellow]⚠️ Some tests failed. Check LLM configuration.[/bold yellow]")

if __name__ == "__main__":
    main()
