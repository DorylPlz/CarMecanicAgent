# 🔧 Mechanical Agent with ADK and Gemini

Intelligent mechanical diagnostic system that uses Google ADK (Agent Development Kit) with Gemini LLM to answer questions about vehicles based on service manuals and internet search.

## 📋 Features

- ✅ **PDF Manual Search**: Efficient indexing of large PDFs (~350MB, 7000+ pages)
- ✅ **Hybrid Search**: Combines semantic search (embeddings) and keyword search
- ✅ **Local Vector Storage**: Uses FAISS for fast search
- ✅ **Internet Search**: Automatic fallback when information is not in the manual
- ✅ **Structured Responses**: Includes page, summary, diagnosis, solution and warnings
- ✅ **Vehicle Agnostic**: Configurable for any vehicle
- ✅ **Multilingual Support**: Responds in the same language as the user's query
- ✅ **Aftermarket Modifications**: Optional configuration for aftermarket parts and modifications

## 🛠️ Technologies

- **Python 3.10+**
- **Google ADK** (Agent Development Kit)
- **Gemini API** (Google Generative AI)
- **FAISS** (Local vector store)
- **Sentence Transformers** (Multilingual embeddings)
- **PyMuPDF** (PDF processing)

## 📦 Installation on Windows 11

### 1. Prerequisites

- Python 3.10 or higher
- Git (optional, for cloning repositories)

### 2. Configure Environment Variables

Create a `.env` file in the project root directory:

```env
# Google API Key (Required)
GOOGLE_API_KEY=your_api_key_here

# LLM Model Configuration (Optional, defaults to gemini-2.5-flash)
LLM_MODEL=gemini-2.5-flash

# Vehicle Configuration (Required)
VEHICLE_MODEL=Your Vehicle Model
VEHICLE_YEAR=2020
VEHICLE_VIN=YourVINNumber

# Optional: Manual PDF path (defaults to service_manual.pdf)
VEHICLE_MANUAL_PDF_PATH=service_manual.pdf

# Optional: Aftermarket modifications (comma-separated or newline-separated)
# Examples:
# VEHICLE_AFTERMARKET_MODS=Intake injen,GoFastBits BHV,Catless downpipe
# Or using newlines:
# VEHICLE_AFTERMARKET_MODS="Intake injen
# GoFastBits BHV
# Catless downpipe"

# Internet search uses Gemini's integrated Google Search
# No additional API keys needed - only GOOGLE_API_KEY is required
```

**Available LLM Models:**
- `gemini-2.5-flash` (default, recommended)
- `gemini-1.5-pro`
- `gemini-1.5-flash`
- `gemini-2.0-flash-exp`

Copy the `.env.example` file to `.env` and fill in your values:

```powershell
copy .env.example .env
# Then edit .env with your actual values
```

### 3. Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you have problems with script execution, run first:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Install Dependencies

```powershell
# Install dependencies
pip install -r requirements.txt
```

**Note**: Installing `faiss-cpu` may take several minutes.

### 5. Prepare the Service Manual

Place your `service_manual.pdf` file in the `CarMecanicAgent/` folder, or specify a different path in the `.env` file:

```
CarMecanicAgent/
  ├── service_manual.pdf  ← Place your PDF here (or configure path in .env)
  ├── agent.py
  ├── main.py
  ├── .env               ← Your configuration file
  └── ...
```

## 🚀 Usage

### First Run (Indexing)

The first time you run the agent, the PDF will be indexed automatically:

```powershell
python main.py
```

**⚠️ Important**: For large PDFs (~350MB), indexing may take:
- Text extraction: 5-10 minutes
- Embedding generation: 10-20 minutes
- Total: ~15-30 minutes

The index is saved in `vector_store/` and is only built once.

You can also build the index separately:

```powershell
python build_index.py
```

### Updating the Service Manual

**⚠️ Important**: If you change the service manual PDF file (replace it with a different manual or update the existing one), you **must delete the `vector_store/` folder** to force the index to be rebuilt with the new manual:

```powershell
# Delete the vector_store folder
Remove-Item -Recurse -Force vector_store

# Then run the agent again - it will rebuild the index automatically
python main.py
```

Or use the build script:

```powershell
# Delete the old index
Remove-Item -Recurse -Force vector_store

# Rebuild the index
python build_index.py
```

**Why?** The index is cached in `vector_store/` for performance. If you change the PDF without deleting this folder, the agent will continue using the old index, which may contain outdated or incorrect information.

### Interactive Chat Mode

```powershell
python main.py
```

Example usage:
```
👤 You: How do I change the engine oil?
🤖 Agent: [Detailed response with steps, pages, warnings...]

👤 You: Why is the brake making noise?
🤖 Agent: [Complete diagnosis...]
```

The agent will respond in the same language as your query (Spanish, English, French, etc.).

### Single Query Mode

```powershell
python main.py "How do I change the air filter?"
```

## 📁 Project Structure

```
CarMecanicAgent/
├── agent.py              # Main ADK agent
├── agent_tools.py        # Agent tools
├── config.py             # Global configuration
├── pdf_indexer.py        # PDF indexer with embeddings
├── internet_search.py    # Internet search
├── main.py               # Main script
├── build_index.py        # Index builder script
├── requirements.txt      # Dependencies
├── README.md             # This file
├── .env.example          # Environment variables template
├── .env                  # Your configuration (not in git)
├── service_manual.pdf    # Service manual (place here or configure path)
└── vector_store/         # Generated index (created automatically)
    ├── faiss_index       # FAISS index
    ├── metadata.json     # Chunk metadata
    └── images_metadata.json  # Image metadata
```

## 🔍 How It Works

### 1. PDF Indexing

- Extracts text from all pages
- Divides into chunks of ~1000 characters with overlap
- Generates embeddings using multilingual model
- Stores in local FAISS index

### 2. Query Processing

1. **Manual Search** (priority):
   - Hybrid search (semantic + keywords)
   - Returns relevant chunks with page number
   - If information is found, uses it

2. **Internet Search** (fallback):
   - Only if there's no information in the manual
   - Uses Gemini's integrated Google Search (no external API keys needed)
   - Returns cited results with sources

### 3. Agent Response

The agent structures the response with:
- 📄 Manual page (if applicable)
- 📝 Content summary
- 🔧 Detailed technical explanation
- 🔍 Diagnostic steps
- 🛠️ Solution steps
- ⚠️ Safety warnings

The agent responds in the same language as the user's query.

## 🔧 Aftermarket Modifications

You can configure aftermarket modifications installed on your vehicle to help the agent provide more accurate diagnoses and recommendations.

### Configuration Methods

#### Method 1: Using `.env` file (Recommended)

Add the `VEHICLE_AFTERMARKET_MODS` variable to your `.env` file:

**Option A: Comma-separated list:**
```env
VEHICLE_AFTERMARKET_MODS=Intake injen,GoFastBits BHV,Catless downpipe
```

**Option B: Newline-separated list (for readability):**
```env
VEHICLE_AFTERMARKET_MODS="Intake injen
GoFastBits BHV
Catless downpipe"
```

#### Method 2: Using Python code

You can also configure modifications programmatically:

```python
from config import Config

# Set all modifications at once
Config.set_aftermarket_modifications([
    "Intake injen",
    "GoFastBits BHV",
    "Catless downpipe"
])

# Or add them one by one
Config.add_aftermarket_modification("Intake injen")
Config.add_aftermarket_modification("GoFastBits BHV")
Config.add_aftermarket_modification("Catless downpipe")
```

### How It Works

When aftermarket modifications are configured:
- The agent is aware of all modifications installed on the vehicle
- The agent considers these modifications when diagnosing problems
- The agent may adapt procedures from the manual based on modifications
- The agent can provide specific advice related to aftermarket parts

**Example:**
If your vehicle has a "Catless downpipe" installed and you ask about exhaust issues, the agent will consider this modification in its diagnosis.

### Viewing Configured Modifications

When you start the agent, configured modifications are displayed:

```
✅ Vehicle: Honda Civic 2021, VIN: 19XFC2F59ME123456
🔧 Aftermarket modifications configured: 3 modification(s)
   • Intake injen
   • GoFastBits BHV
   • Catless downpipe
```

## 🐛 Troubleshooting

### Error: "GOOGLE_API_KEY not found in .env file"

Make sure you have created a `.env` file with your API key:

```powershell
# Check if .env exists
Test-Path .env

# If not, copy from example
copy .env.example .env
# Then edit .env and add your GOOGLE_API_KEY
```

### Error: "Vehicle variables not found in .env"

Add the required vehicle configuration to your `.env` file:

```env
VEHICLE_MODEL=Your Vehicle Model
VEHICLE_YEAR=2020
VEHICLE_VIN=YourVINNumber
```

### Error installing FAISS

If you have problems with `faiss-cpu`, try:

```powershell
pip install --upgrade pip
pip install faiss-cpu --no-cache-dir
```

### Error: "Index not found"

Make sure the PDF exists and run the agent. It will be indexed automatically.

### Outdated Index After Changing Manual

If you've replaced or updated the service manual PDF but the agent is still using old information:

1. **Delete the `vector_store/` folder**:
   ```powershell
   Remove-Item -Recurse -Force vector_store
   ```

2. **Run the agent again** - it will automatically rebuild the index:
   ```powershell
   python main.py
   ```

The index is cached for performance, so it won't automatically detect when the PDF file changes. You must manually delete `vector_store/` to force a rebuild.

### Insufficient Memory

For very large PDFs, you can:
- Reduce `CHUNK_SIZE` in `config.py`
- Use a smaller embedding model
- Increase available RAM

### Model Not Available

If the configured LLM model is not available, try changing it in `.env`:

```env
LLM_MODEL=gemini-1.5-flash
```

## 📝 Example Response

**Query**: "How do I change the engine oil?"

**Agent Response**:

```
📖 Information found in manual:
📄 Relevant pages: 245, 246, 247

**Content Summary**
Engine oil change should be performed every 10,000 km or 6 months...

**Detailed Technical Explanation**
Engine oil lubricates internal components and must be changed regularly...

**Diagnostic Steps**
1. Check current oil level using the dipstick
2. Review oil color and consistency
3. Check date of last change...

**Solution Steps**
1. Warm up the engine for 5 minutes
2. Turn off the engine and wait 2 minutes
3. Place container under the drain plug...
[continues...]

**Safety Warnings**
⚠️ Oil may be very hot. Use protective gloves.
⚠️ Do not pour used oil down the drain.
⚠️ Make sure the vehicle is on level ground.
```

## 🔐 Security

- ⚠️ Never share your `GOOGLE_API_KEY`
- ⚠️ Do not upload the `.env` file to public repositories
- ⚠️ The PDF index is stored locally (not sent to the internet)
- ⚠️ The `.env` file is already in `.gitignore`

## 📚 Resources

- [Google ADK Documentation](https://github.com/google/adk)
- [Gemini API](https://ai.google.dev/)
- [FAISS Documentation](https://github.com/facebookresearch/faiss)

## 📄 License

This project is for educational and personal use.

---

**Developed with ❤️ using Google ADK and Gemini**
