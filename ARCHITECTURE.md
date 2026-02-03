# QuantumDev-v2 Architecture

## Overview
QuantumDev-v2 is an AI-powered software factory that automatically generates complete software projects using DeepSeek R1 reasoning capabilities.

## Infrastructure

### GPU Node (Vast.ai)
- **Hardware:** 48GB VRAM
- **Model:** DeepSeek R1 Distill Qwen 32B Abliterated Q6 (~26GB)
- **Endpoint:** localhost:5000
- **Connection:** SSH reverse tunnel to VPS

### VPS Node (Contabo)
- **Hardware:** 12GB RAM
- **Role:** Orchestrator and API backend
- **Services:** FastAPI (port 8001), ChromaDB, Redis (optional)

## Architecture

### Directory Structure

```
QuantumDev-v2/
├── hub.py                 # Main entry point (refactored)
├── core/
│   ├── llm_client.py     # Unified LLM client (NEW)
│   ├── schemas.py        # Pydantic models (NEW)
│   ├── engine.py         # FastAPI backend
│   ├── tools.py          # Tool implementations
│   └── vector_memory.py  # ChromaDB integration
├── projects/             # Generated software
├── memories/             # Conversation sessions
├── tests/               # Test suite
└── logs/                # Application logs (NEW)
```

### Core Modules

#### llm_client.py (NEW)
Centralizes all LLM interactions with:
- Automatic retry with exponential backoff
- DeepSeek R1 `<think>` tag cleaning
- Code block extraction with escape sequence handling
- Timeout management (300s default)

**Key Methods:**
- `generate()`: Main LLM call with retry logic
- `clean_think_tags()`: Removes reasoning blocks from output
- `extract_code_block()`: Parses markdown code blocks with unescape support

#### schemas.py (NEW)
Pydantic models for type-safe validation:

**Blueprint**: File list validation
- Ensures valid extensions (.py, .txt, .md, .json, .yml, .yaml, .toml, .cfg)
- Auto-adds main.py and requirements.txt
- Prevents library names being used as filenames

**CodeFile**: Generated file metadata
- Content validation (min 10 chars)
- Auto-calculates file size
- Tracks generation attempts

**ProjectState**: Crash recovery state
- Valid phases: blueprint_complete, construction_in_progress, construction_complete, integration_complete, testing_complete
- Expiration check (24h default)
- Timestamp tracking

#### hub.py (Refactored)
Main orchestrator with three operational modes:

1. **Software House Mode** (`/hub`)
   - Automated project generation
   - Blueprint → Construction → Integration → Testing
   - Crash recovery with `.build_state.json`

2. **Chat Mode** (`/chat`)
   - Interactive AI conversations
   - Session persistence in `memories/`
   - Max history: 30 messages

3. **Roadmap Mode** (Legacy - being deprecated)

#### engine.py
FastAPI backend serving:
- `/chat/god-mode`: Main LLM endpoint
- `/tools/*`: Tool execution endpoints
- Health checks and metrics

#### tools.py
External integrations:
- Web scraping (BeautifulSoup)
- File system operations
- Database connections
- API calls

#### vector_memory.py
ChromaDB-based semantic memory:
- Conversation indexing
- Similarity search
- Context retrieval

## Data Flow

### Software House Mode
```
User Input → Blueprint Generation → File List Validation (Pydantic)
             ↓
           For each file:
             - Generate code via LLM
             - Extract & validate with CodeFile schema
             - Save to disk
             - Update ProjectState
             ↓
           Integration Phase:
             - Dependency installation
             - Syntax checks
             ↓
           Testing Phase:
             - Execute main.py
             - Self-healing on errors
```

### LLM Request Flow
```
hub.py: call_ai()
  ↓
LLMClient.generate()
  ├── Retry Loop (max 3 attempts)
  │   ├── POST /chat/god-mode
  │   ├── Exponential backoff on timeout
  │   └── Error handling
  ↓
Response Processing
  ├── clean_think_tags() if needed
  ├── extract_code_block() for code
  └── Return to caller
```

## Configuration

### Environment Variables
```bash
API_URL=http://localhost:8001/chat/god-mode  # LLM endpoint
BASE_DIR=projects                             # Project output directory
MEMORY_DIR=memories                           # Chat session storage
MAX_HISTORY_LENGTH=30                         # Conversation context limit
```

### Logging
- **Level:** INFO
- **Output:** Console + `logs/quantumdev.log`
- **Format:** `%(asctime)s [%(levelname)s] %(name)s: %(message)s`

## Build State Recovery

Projects save progress to `.build_state.json`:
```json
{
  "phase": "construction_in_progress",
  "blueprint": ["main.py", "utils.py", "requirements.txt"],
  "completed_files": ["requirements.txt"],
  "goal": "Create a web scraper",
  "timestamp": 1738577891.5
}
```

On crash/restart:
1. Load state with `ProjectState.parse_raw()`
2. Validate phase and expiration
3. Resume from `completed_files`

## Security & Reliability

### Input Validation
- Pydantic schemas enforce type safety
- File extension whitelist
- Path traversal prevention

### Error Handling
- Exponential backoff on API timeouts
- Graceful degradation on partial failures
- Self-healing code generation (up to 3 attempts per file)

### Monitoring
- Structured logging with timestamps
- Request/response size tracking
- Generation attempt metrics

## Deployment

### Docker Setup
```bash
docker-compose up -d  # Starts FastAPI + ChromaDB
```

### Manual Setup
```bash
pip install -r requirements.txt
python hub.py  # Interactive mode
```

## Future Enhancements
- Multi-model support (GPT-4, Claude)
- Real-time collaboration (WebSocket)
- Plugin system for custom tools
- CI/CD integration
- Distributed task queue (Celery)
