"""
PDF indexer with embeddings and vector storage.
Implements chunk-based indexing, lazy loading and hybrid search.
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import fitz  # PyMuPDF
from tqdm import tqdm
import pickle

from config import Config


class PDFIndexer:
    """PDF indexer with embeddings and vector search."""
    
    def __init__(self):
        """Initializes the indexer."""
        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict] = []
        self.chunks: List[str] = []
        self.images_metadata: Dict[int, List[Dict]] = {}  # Page -> List of images
        
    def extract_images_from_page(self, page, page_num: int) -> List[Dict]:
        """
        Extracts information about images/diagrams from a page.
        Returns a list of dictionaries with image information.
        """
        images_info = []
        try:
            # Get list of images on the page
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                # img is a tuple: (xref, smask, width, height, bpc, colorspace, alt, name, filter, referencer)
                xref = img[0]
                width = img[2]
                height = img[3]
                
                # Get rectangles where the image appears
                image_rects = page.get_image_rects(xref)
                
                for rect in image_rects:
                    images_info.append({
                        "xref": xref,
                        "index": img_index,
                        "width": width,
                        "height": height,
                        "rect": {
                            "x0": rect.x0,
                            "y0": rect.y0,
                            "x1": rect.x1,
                            "y1": rect.y1
                        },
                        "area": (rect.x1 - rect.x0) * (rect.y1 - rect.y0)  # Area to determine size
                    })
        except Exception as e:
            # If there's an error, continue without images
            pass
        
        return images_info
    
    def extract_text_from_pdf(self, pdf_path: Path) -> List[Tuple[str, int]]:
        """
        Extracts text from PDF with page information.
        Also extracts information about images/diagrams.
        Returns a list of tuples (text, page_number).
        """
        print(f"📖 Extracting text and images from {pdf_path}...")
        doc = fitz.open(pdf_path)
        pages_text = []
        
        # Create folder for images if it doesn't exist
        Config.IMAGES_PATH.mkdir(parents=True, exist_ok=True)
        
        for page_num in tqdm(range(len(doc)), desc="Processing pages"):
            page = doc[page_num]
            text = page.get_text()
            
            # Extract image information
            images_info = self.extract_images_from_page(page, page_num + 1)
            if images_info:
                self.images_metadata[page_num + 1] = images_info
            
            if text.strip():
                pages_text.append((text, page_num + 1))
        
        doc.close()
        print(f"✅ Extracted {len(pages_text)} pages with content")
        print(f"✅ Detected images on {len(self.images_metadata)} pages")
        return pages_text
    
    def create_chunks(self, pages_text: List[Tuple[str, int]]) -> List[Dict]:
        """
        Divides text into chunks with metadata.
        Returns a list of dictionaries with chunk, page, and position.
        """
        print("✂️ Creating text chunks...")
        chunks = []
        
        for text, page_num in pages_text:
            # Split text into chunks
            text_length = len(text)
            start = 0
            
            while start < text_length:
                end = start + Config.CHUNK_SIZE
                chunk_text = text[start:end]
                
                if chunk_text.strip():
                    chunks.append({
                        "text": chunk_text.strip(),
                        "page": page_num,
                        "start_pos": start,
                        "end_pos": min(end, text_length)
                    })
                
                # Move start with overlap
                start = end - Config.CHUNK_OVERLAP
                if start >= text_length:
                    break
        
        print(f"✅ Created {len(chunks)} chunks")
        return chunks
    
    def generate_embeddings(self, chunks: List[Dict]) -> np.ndarray:
        """Generates embeddings for all chunks."""
        print("🧮 Generating embeddings...")
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            batch_size=32,
            convert_to_numpy=True
        )
        print(f"✅ Generated {len(embeddings)} embeddings of dimension {embeddings.shape[1]}")
        return embeddings
    
    def build_index(self, pdf_path: Optional[Path] = None) -> None:
        """
        Builds the complete PDF index.
        If the index already exists, loads it instead of rebuilding.
        If image metadata is missing, extracts it.
        """
        pdf_path = pdf_path or Config.MANUAL_PDF_PATH
        
        # Check if index already exists
        if Config.INDEX_PATH.exists() and Config.METADATA_PATH.exists():
            print("📂 Existing index found. Loading...")
            self.load_index()
            
            # If image metadata is missing, extract it
            if not Config.IMAGES_METADATA_PATH.exists() or not self.images_metadata:
                print("📷 Image metadata not found. Extracting images...")
                self._extract_images_metadata(pdf_path)
            return
        
        # Create directory if it doesn't exist
        Config.VECTOR_STORE_PATH.mkdir(exist_ok=True)
        
        # Extract text
        pages_text = self.extract_text_from_pdf(pdf_path)
        
        # Create chunks
        chunks = self.create_chunks(pages_text)
        self.chunks = chunks
        
        # Generate embeddings
        embeddings = self.generate_embeddings(chunks)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        
        # Save metadata
        self.metadata = chunks
        
        # Save index
        self.save_index()
        
        # Save image metadata
        if self.images_metadata:
            with open(Config.IMAGES_METADATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.images_metadata, f, ensure_ascii=False, indent=2)
        
        print("✅ Index built and saved successfully")
    
    def _extract_images_metadata(self, pdf_path: Path) -> None:
        """
        Extracts image metadata from an already indexed PDF.
        """
        print(f"📷 Extracting image information from {pdf_path}...")
        doc = fitz.open(pdf_path)
        
        for page_num in tqdm(range(len(doc)), desc="Extracting images"):
            page = doc[page_num]
            images_info = self.extract_images_from_page(page, page_num + 1)
            if images_info:
                self.images_metadata[page_num + 1] = images_info
        
        doc.close()
        
        # Save image metadata
        if self.images_metadata:
            with open(Config.IMAGES_METADATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.images_metadata, f, ensure_ascii=False, indent=2)
            print(f"✅ Image metadata saved: {len(self.images_metadata)} pages with images")
        else:
            print("⚠️ No images found in PDF")
    
    def save_index(self) -> None:
        """Saves index and metadata to disk."""
        print("💾 Saving index...")
        
        # Save FAISS index
        faiss.write_index(self.index, str(Config.INDEX_PATH))
        
        # Save metadata
        with open(Config.METADATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        
        # Save image metadata
        with open(Config.IMAGES_METADATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.images_metadata, f, ensure_ascii=False, indent=2)
        
        print("✅ Index saved")
    
    def load_index(self) -> None:
        """Loads index and metadata from disk."""
        print("📂 Loading index...")
        
        if not Config.INDEX_PATH.exists():
            raise FileNotFoundError(f"Index not found at {Config.INDEX_PATH}")
        
        # Load FAISS index
        self.index = faiss.read_index(str(Config.INDEX_PATH))
        
        # Load metadata
        with open(Config.METADATA_PATH, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
        
        # Load image metadata if it exists
        if Config.IMAGES_METADATA_PATH.exists():
            with open(Config.IMAGES_METADATA_PATH, 'r', encoding='utf-8') as f:
                self.images_metadata = json.load(f)
            # Convert keys from string to int
            self.images_metadata = {int(k): v for k, v in self.images_metadata.items()}
        
        print(f"✅ Index loaded: {len(self.metadata)} chunks available")
        if self.images_metadata:
            print(f"✅ Image metadata loaded: {len(self.images_metadata)} pages with images")
    
    def search_semantic(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Semantic search using embeddings.
        Returns a list of results with text, page and score.
        """
        if self.index is None or len(self.metadata) == 0:
            raise ValueError("Index not initialized. Run build_index() first.")
        
        top_k = top_k or Config.TOP_K_RESULTS
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode(
            [query],
            convert_to_numpy=True
        ).astype('float32')
        
        # Search in index
        distances, indices = self.index.search(query_embedding, top_k)
        
        # Format results
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.metadata):
                similarity = 1 / (1 + distance)  # Convert distance to similarity
                if similarity >= Config.SIMILARITY_THRESHOLD:
                    chunk_data = self.metadata[idx]
                    results.append({
                        "text": chunk_data["text"],
                        "page": chunk_data["page"],
                        "similarity": float(similarity),
                        "type": "semantic"
                    })
        
        return results
    
    def search_keyword(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Keyword search (keyword matching).
        Returns a list of results with text, page and score.
        """
        if len(self.metadata) == 0:
            raise ValueError("Metadata not loaded. Run build_index() first.")
        
        top_k = top_k or Config.TOP_K_RESULTS
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_chunks = []
        
        for chunk_data in self.metadata:
            text_lower = chunk_data["text"].lower()
            text_words = set(text_lower.split())
            
            # Calculate score: number of matching words
            matches = len(query_words.intersection(text_words))
            if matches > 0:
                score = matches / len(query_words)
                scored_chunks.append({
                    "text": chunk_data["text"],
                    "page": chunk_data["page"],
                    "similarity": score,
                    "type": "keyword"
                })
        
        # Sort by score and return top_k
        scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_chunks[:top_k]
    
    def search_hybrid(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Hybrid search: combines semantic and keyword search.
        Returns merged and deduplicated results.
        """
        top_k = top_k or Config.TOP_K_RESULTS
        
        # Perform both searches
        semantic_results = self.search_semantic(query, top_k * 2)
        keyword_results = self.search_keyword(query, top_k * 2)
        
        # Merge results
        # Use a dictionary to deduplicate by page and similar text
        merged = {}
        
        # Add semantic results (higher weight)
        for result in semantic_results:
            key = (result["page"], result["text"][:100])  # Use first 100 chars as key
            if key not in merged or merged[key]["similarity"] < result["similarity"]:
                merged[key] = result
        
        # Add keyword results (lower weight)
        for result in keyword_results:
            key = (result["page"], result["text"][:100])
            if key not in merged:
                # Reduce keyword score to prioritize semantic
                result["similarity"] = result["similarity"] * 0.7
                merged[key] = result
            elif merged[key]["type"] == "keyword":
                # If both are keyword, keep the best
                if result["similarity"] > merged[key]["similarity"]:
                    merged[key] = result
        
        # Convert to list and sort
        results = list(merged.values())
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results[:top_k]
    
    def get_images_for_page(self, page_num: int) -> List[Dict]:
        """
        Returns information about images/diagrams on a specific page.
        
        Args:
            page_num: Page number
            
        Returns:
            List of dictionaries with image information
        """
        return self.images_metadata.get(page_num, [])
    
    def extract_image_from_pdf(self, pdf_path: Path, page_num: int, image_xref: int, output_path: Optional[Path] = None) -> Optional[Path]:
        """
        Extracts a specific image from the PDF and saves it.
        
        Args:
            pdf_path: Path to PDF
            page_num: Page number (1-indexed)
            image_xref: Image XREF
            output_path: Path where to save the image (optional)
            
        Returns:
            Path where the image was saved or None if there's an error
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num - 1]  # Convert to 0-indexed
            
            # Extract image
            image = doc.extract_image(image_xref)
            image_bytes = image["image"]
            image_ext = image["ext"]
            
            # Generate filename if not provided
            if output_path is None:
                Config.IMAGES_PATH.mkdir(parents=True, exist_ok=True)
                output_path = Config.IMAGES_PATH / f"page_{page_num}_img_{image_xref}.{image_ext}"
            
            # Save image
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            
            doc.close()
            return output_path
        except Exception as e:
            print(f"⚠️ Error extracting image: {e}")
            return None

