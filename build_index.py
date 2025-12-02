"""
Script to build the PDF service manual index.
Use it if you want to index the PDF before running the agent.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from config import Config
from pdf_indexer import PDFIndexer


def main():
    """Builds the service manual index."""
    print("="*60)
    print("📚 Service Manual Index Builder")
    print("="*60)
    print()
    
    # Verify PDF exists
    pdf_path = Config.MANUAL_PDF_PATH
    
    if not pdf_path.exists():
        print(f"❌ Error: File {pdf_path} not found")
        print(f"   Place the service_manual.pdf file in: {Config.BASE_DIR}")
        sys.exit(1)
    
    print(f"📄 PDF file: {pdf_path}")
    print(f"📊 Size: {pdf_path.stat().st_size / (1024*1024):.2f} MB")
    print()
    
    # Check if index already exists
    if Config.INDEX_PATH.exists():
        response = input("⚠️  Index already exists. Do you want to rebuild it? (y/n): ")
        if response.lower() != 'y':
            print("✅ Operation cancelled. Using existing index.")
            return
    
    print("🚀 Starting indexing...")
    print("⚠️  This may take 15-30 minutes for large PDFs (~350MB)\n")
    
    try:
        indexer = PDFIndexer()
        indexer.build_index(pdf_path)
        print("\n✅ Index built successfully!")
        print(f"📂 Location: {Config.VECTOR_STORE_PATH}")
    except Exception as e:
        print(f"\n❌ Error during indexing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
