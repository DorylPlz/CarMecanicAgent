# 📝 Technical Notes

## ⚠️ Potential Adjustments for ADK

The code is designed to work with Google ADK, but depending on the specific version of ADK you use, some minor adjustments may be necessary:

### 1. Custom Tool Execution

If ADK doesn't automatically execute custom tool functions, you may need:

**Option A**: Use a tool callback or handler
```python
# In agent.py, modify the Runner to include tool handler
def tool_handler(function_name, arguments):
    if function_name in TOOL_FUNCTIONS:
        return TOOL_FUNCTIONS[function_name](**arguments)
    return None

self.runner = Runner(
    agent=self.agent,
    session_service=self.session_service,
    tool_handler=tool_handler  # If ADK supports it
)
```

**Option B**: Use ADK's built-in tools and adapt them
```python
# If ADK has built-in tools, you can adapt them
from google.adk.tools import google_search

# Create custom wrapper
def custom_manual_search(query):
    # Your logic here
    pass
```

### 2. ADK Version

Check the installed ADK version:
```bash
pip show google-adk
```

If there are incompatibilities, consult the official documentation:
- GitHub: https://github.com/google/adk
- Documentation: (check Google's official documentation)

### 3. Gemini Models

The code uses `gemini-2.5-flash` by default. If this model is not available, change to:
- `gemini-1.5-pro`
- `gemini-1.5-flash`
- `gemini-2.5-flash`

In `agent.py`:
```python
agent = MechanicalAgent(model="gemini-1.5-flash")
```

Or configure it in `.env`:
```env
LLM_MODEL=gemini-1.5-flash
```

### 4. Asynchronous Processing

If ADK requires asynchronous processing, you can modify `agent.py`:

```python
import asyncio

async def query_async(self, query: str, session_id: str = "default"):
    response = await self.runner.run_async(
        message=query,
        session_id=session_id
    )
    return response.text
```

### 5. Runner Response Format

If `runner.run()` returns a different format, adjust the `query()` method:

```python
def query(self, query: str, session_id: str = "default") -> str:
    try:
        response = self.runner.run(
            message=query,
            session_id=session_id
        )
        
        # Adjust according to the actual response format
        if hasattr(response, 'content'):
            return response.content.text
        elif hasattr(response, 'text'):
            return response.text
        elif isinstance(response, str):
            return response
        else:
            # Try to extract text from different formats
            return str(response)
            
    except Exception as e:
        return f"Error processing query: {str(e)}"
```

## 🔧 Common Problem Solving

### Error: "Tool not found" or "Function not executable"

1. Verify that `TOOL_FUNCTIONS` is correctly defined
2. Make sure functions are in global scope
3. Consider using a tool registration approach if ADK requires it

### Error: "Index not found"

1. Run `python build_index.py` first
2. Verify that `service_manual.pdf` exists (or the path configured in `.env`)
3. Make sure you have write permissions in the folder

### Error: "API Key not found"

1. Verify that `GOOGLE_API_KEY` is configured in your `.env` file:
   ```env
   GOOGLE_API_KEY=your_api_key_here
   ```
2. Make sure the `.env` file is in the project root directory

### Slow Performance

1. For large PDFs, initial indexing is slow (15-30 min)
2. Search should be fast after indexing
3. Consider using a faster model like `gemini-1.5-flash`

## 🔄 Process Flow Diagrams

### Complete Process Flow: From User Question to Response

The following diagrams show the complete flow of how the system processes a user's question from start to finish.

#### Phase 1: Initialization (One-time setup when starting)

```
main.py::main()
  ├─> Config.load_vehicle_from_env()
  │   └─> Config.set_vehicle() → Creates VehicleConfig
  │
  ├─> build_index_if_needed()
  │   └─> PDFIndexer.build_index() (only if index doesn't exist)
  │
  └─> MechanicalAgent.__init__()
      ├─> setup_tools() [agent_tools.py]
      │   ├─> PDFIndexer() → Initializes embedding model
      │   ├─> pdf_indexer.load_index() → Loads FAISS index
      │   └─> InternetSearch() → Initializes internet searcher
      │
      ├─> Agent() [Google ADK] → Creates agent with instructions
      └─> Runner() → Creates runner to execute queries
```

#### Phase 2: Processing User Question

```
main.py::main()
  └─> agent.query(query) [agent.py::MechanicalAgent.query()]
      │
      ├─> _ensure_session() → Ensures session exists
      │
      └─> runner.run_async() [Google ADK]
          │
          └─> ADK processes question and decides to use tools
              │
              ├─> If needs to search manual:
              │   └─> search_manual(query) [agent_tools.py]
              │       │
              │       ├─> pdf_indexer.search_hybrid(query) [pdf_indexer.py]
              │       │   │
              │       │   ├─> search_semantic(query) [pdf_indexer.py]
              │       │   │   ├─> embedding_model.encode(query) → Generates embedding
              │       │   │   ├─> index.search(embedding) → Searches in FAISS
              │       │   │   └─> Calculates similarity (1 / (1 + distance))
              │       │   │
              │       │   └─> search_keyword(query) [pdf_indexer.py]
              │       │       ├─> Splits query into words
              │       │       ├─> Searches matches in metadata
              │       │       └─> Calculates score (matches / total_words)
              │       │
              │       ├─> Merges semantic + keyword results
              │       ├─> Removes duplicates
              │       ├─> Sorts by relevance
              │       │
              │       ├─> Enhances query with English terms (if Spanish terms found)
              │       └─> Formats response with:
              │           - Page number
              │           - Chunk content
              │           - Image/diagram information
              │
              └─> If not found in manual (fallback):
                  └─> search_internet(query) [agent_tools.py]
                      │
                      └─> internet_searcher.search(query) [internet_search.py]
                          │
                          └─> Uses Gemini's integrated Google Search
                              │   (No external API keys needed)
                              │
                              └─> Returns formatted results with sources
```

#### Phase 3: Final Response Generation

```
ADK Runner (continues)
  │
  ├─> Receives results from tools
  │
  ├─> Gemini LLM processes:
  │   - User question
  │   - Manual results (if any)
  │   - Internet results (if used)
  │   - Agent instructions
  │   - Vehicle context
  │
  └─> Generates final response in user's language
      │
      └─> agent.query() returns response
          │
          └─> main.py displays response to user
```

### Simplified Flow Diagram

```
User asks question
    ↓
main.py::agent.query()
    ↓
Google ADK Runner
    ↓
ADK decides to use tool
    ↓
┌─────────────────────────────┐
│  search_manual(query)       │
│  [agent_tools.py]           │
│    ↓                        │
│  search_hybrid()            │
│  [pdf_indexer.py]           │
│    ├─> search_semantic()    │ ← Embeddings + FAISS
│    └─> search_keyword()     │ ← Word matching
│    ↓                        │
│  Formats results            │
└─────────────────────────────┘
    ↓
ADK receives results
    ↓
┌─────────────────────────────┐
│  Gemini LLM processes:      │
│  - Question                 │
│  - Manual results           │
│  - Instructions             │
│  - Vehicle context          │
└─────────────────────────────┘
    ↓
Generates response (same language)
    ↓
User receives response
```

### Key Functions in Execution Order

1. `main.py::main()` - Entry point
2. `main.py::agent.query()` - Starts processing
3. `agent.py::MechanicalAgent.query()` - Processes query
4. `agent.py::_ensure_session()` - Manages session
5. `agent_tools.py::search_manual()` - Manual search (priority)
6. `pdf_indexer.py::search_hybrid()` - Hybrid search
7. `pdf_indexer.py::search_semantic()` - Embedding search
8. `pdf_indexer.py::search_keyword()` - Keyword search
9. `agent_tools.py::search_internet()` - Internet search (fallback)
10. `internet_search.py::search()` - Executes internet search
11. Gemini LLM - Generates final response
12. `main.py` - Displays response to user

### Important Features

- **Hybrid Search**: Combines semantic (embeddings) and keyword search
- **Priority**: Manual first, then internet
- **Multilingual**: Responds in the same language as the question
- **Context**: Includes vehicle information in searches
- **Sessions**: Maintains context between questions

The system prioritizes the service manual and uses the internet only as a fallback.

## 📚 Additional Resources

- [Google ADK GitHub](https://github.com/google/adk)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [FAISS Documentation](https://github.com/facebookresearch/faiss)

