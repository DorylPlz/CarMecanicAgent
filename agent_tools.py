"""
Custom tools for the ADK agent.
Includes manual search and internet search.
"""
from typing import List, Dict, Optional

from pdf_indexer import PDFIndexer
from internet_search import InternetSearch
from config import Config


# Global instances (initialized in setup_tools)
pdf_indexer: Optional[PDFIndexer] = None
internet_searcher: Optional[InternetSearch] = None


def setup_tools():
    """Initializes agent tools."""
    global pdf_indexer, internet_searcher
    
    # Initialize PDF indexer
    pdf_indexer = PDFIndexer()
    if Config.INDEX_PATH.exists():
        pdf_indexer.load_index()
    else:
        print("⚠️ Index not found. Run build_index() first.")
    
    # Initialize internet searcher
    internet_searcher = InternetSearch()


def search_manual(query: str) -> str:
    """
    Searches for technical information in the vehicle service manual.
    
    The manual is in English and has over 7000 pages. Searches exhaustively
    using terms in English and other languages. Returns page number and complete content.
    
    Args:
        query: Query about the mechanical problem or topic to search in the manual
        
    Returns:
        Formatted response with manual information or message if not found
    """
    if pdf_indexer is None:
        return "Error: PDF indexer is not initialized."
    
    try:
        # Perform multiple searches with variations
        all_results = []
        
        # Original search
        results = pdf_indexer.search_hybrid(query, top_k=Config.TOP_K_RESULTS * 2)
        all_results.extend(results)
        
        # Search with common English terms
        english_terms = {
            'pastillas': 'brake pads',
            'frenos': 'brake',
            'caliper': 'caliper',
            'cáliper': 'caliper',
            'cambio': 'replace replacement',
            'reemplazo': 'replace replacement',
            'delantero': 'front',
            'trasero': 'rear'
        }
        
        # Add English terms if they are in the query
        enhanced_query = query
        for es_term, en_term in english_terms.items():
            if es_term.lower() in query.lower():
                enhanced_query += f" {en_term}"
        
        if enhanced_query != query:
            results_en = pdf_indexer.search_hybrid(enhanced_query, top_k=Config.TOP_K_RESULTS)
            all_results.extend(results_en)
        
        # Remove duplicates keeping the best score
        seen_pages = {}
        for result in all_results:
            key = (result['page'], result['text'][:100])  # Use page and first 100 chars as key
            if key not in seen_pages or result['similarity'] > seen_pages[key]['similarity']:
                seen_pages[key] = result
        
        results = list(seen_pages.values())
        results.sort(key=lambda x: x['similarity'], reverse=True)
        results = results[:Config.TOP_K_RESULTS]
        
        if not results:
            return "No relevant information found in the service manual."
        
        # Format response with more content
        response = f"📖 Information found in manual:\n\n"
        
        for i, result in enumerate(results, 1):
            page_num = result['page']
            response += f"**Result {i} - Page {page_num}**\n"
            response += f"Relevance: {result['similarity']:.2%}\n"
            
            # Check if there are images/diagrams on this page
            images_info = pdf_indexer.get_images_for_page(page_num)
            if images_info:
                response += f"📷 This page contains {len(images_info)} reference diagram(s)/image(s)\n"
            
            # Show more content (up to 1000 characters)
            content = result['text']
            if len(content) > 1000:
                content = content[:1000] + "..."
            response += f"Content: {content}\n\n"
        
        # Consolidated summary with image information
        pages = sorted(set(r["page"] for r in results))
        pages_with_images = []
        for page_num in pages:
            if pdf_indexer.get_images_for_page(page_num):
                pages_with_images.append(page_num)
        
        response += f"\n📄 Relevant pages: {', '.join(map(str, pages))}\n"
        if pages_with_images:
            response += f"📷 Pages with diagrams/images: {', '.join(map(str, pages_with_images))}\n"
            response += f"\n💡 Note: The mentioned pages contain reference diagrams and images that complement the textual information.\n"
        
        return response
        
    except Exception as e:
        return f"Error searching manual: {str(e)}"


def search_internet(query: str) -> str:
    """
    Searches for information on the internet using Gemini's integrated Google Search.
    Use this tool ONLY as a fallback after having tried searching the manual.
    Useful for general information, recent updates or problems not documented in the manual.
    
    This uses Gemini's native search capabilities - no external API keys needed.
    Only requires GOOGLE_API_KEY which is already configured for the agent.
    
    IMPORTANT: When this tool is used, the agent MUST:
    1. Clearly indicate that internet search was performed
    2. Include all sources at the end of the response
    
    Args:
        query: Query about the mechanical problem to search on the internet
        
    Returns:
        Formatted response with internet results and sources
    """
    if internet_searcher is None:
        return "Error: Internet searcher is not initialized."
    
    try:
        # Add vehicle context to search
        vehicle_info = Config.get_vehicle_info()
        enhanced_query = f"{query} {vehicle_info}"
        
        # The search() method returns formatted results with sources
        results = internet_searcher.search(enhanced_query, num_results=5)
        
        return results
        
    except Exception as e:
        return f"Error searching internet: {str(e)}"


# Define tools for ADK
# ADK expects callable functions directly
def get_tools():
    """Returns configured tools for the ADK agent."""
    # ADK can use functions directly
    # Functions must have descriptive docstrings for ADK to understand them
    return [search_manual, search_internet]


# Function mapping for the agent
TOOL_FUNCTIONS = {
    "search_manual": search_manual,
    "search_internet": search_internet
}
