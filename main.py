"""
Main script to run the mechanical agent.
Example usage and vehicle configuration.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from config import Config
from pdf_indexer import PDFIndexer
from agent import MechanicalAgent


def build_index_if_needed():
    """Builds the PDF index if it doesn't exist."""
    if Config.INDEX_PATH.exists():
        print("✅ Index already exists. Skipping indexing.\n")
        return
    
    print("📚 Building manual index...")
    print("⚠️ This may take several minutes for large PDFs (~350MB)\n")
    
    indexer = PDFIndexer()
    indexer.build_index()
    print("\n✅ Index built successfully\n")


def main():
    """Main function."""
    print("="*60)
    print("🔧 Mechanical Agent - Diagnostic System")
    print("="*60)
    print()
    
    # Verify API key
    if not Config.GOOGLE_API_KEY:
        print("❌ Error: GOOGLE_API_KEY not found in .env file")
        print("   Create a .env file with the following variable:")
        print("   GOOGLE_API_KEY=your_api_key")
        sys.exit(1)
    
    # Configure vehicle from .env
    print("📋 Configuring vehicle...")
    vehicle = Config.load_vehicle_from_env()
    
    if vehicle is None:
        print("❌ Error: Vehicle configuration not found in .env file")
        print()
        print("   Please configure your vehicle by adding the following variables to your .env file:")
        print()
        print("   VEHICLE_MODEL=Your Vehicle Model")
        print("   VEHICLE_YEAR=2020")
        print("   VEHICLE_VIN=YourVINNumber")
        print("   (Optional) VEHICLE_MANUAL_PDF_PATH=service_manual.pdf")
        sys.exit(1)
    
    print(f"✅ {Config.get_vehicle_info()}")
    
    # Load aftermarket modifications from .env (optional)
    Config.load_aftermarket_mods_from_env()
    aftermarket_mods = Config.get_aftermarket_modifications()
    if aftermarket_mods:
        print(f"🔧 Aftermarket modifications configured: {len(aftermarket_mods)} modification(s)")
        for mod in aftermarket_mods:
            print(f"   • {mod}")
    print()
    
    # Verify PDF exists
    if not Config.MANUAL_PDF_PATH.exists():
        print(f"⚠️ Warning: {Config.MANUAL_PDF_PATH} not found")
        print("   The agent will work but will only be able to search the internet.\n")
    else:
        # Build index if needed
        build_index_if_needed()
    
    # Initialize agent
    print("🤖 Initializing agent...")
    try:
        agent = MechanicalAgent(model=Config.LLM_MODEL)
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        sys.exit(1)
    
    # Usage mode
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        print(f"\n📝 Query: {query}\n")
        response = agent.query(query)
        print("🤖 Response:")
        print("-" * 60)
        print(response)
        print("-" * 60)
    else:
        # Interactive chat mode
        agent.chat()


if __name__ == "__main__":
    main()
