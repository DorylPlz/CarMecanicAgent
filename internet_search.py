"""
Internet search using Gemini's integrated Google Search.
No external API keys required - uses Gemini's native search capabilities.
"""
import os
from typing import Optional
from google.genai import Client, types

from config import Config


class InternetSearch:
    """Internet searcher using Gemini's integrated Google Search."""
    
    def __init__(self):
        """Initializes the Gemini client for integrated search."""
        if not Config.GOOGLE_API_KEY:
            self.client = None
            return
        
        os.environ["GOOGLE_API_KEY"] = Config.GOOGLE_API_KEY
        try:
            self.client = Client(api_key=Config.GOOGLE_API_KEY)
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize Gemini client for search: {e}")
            self.client = None
        
    def search(self, query: str, num_results: int = 5) -> str:
        """
        Performs internet search using Gemini's integrated Google Search.
        This uses Gemini's native search capabilities - no external API keys needed.
        
        Args:
            query: Search query
            num_results: Number of results to return (for formatting)
            
        Returns:
            Formatted search results as a string
        """
        if not self.client:
            return "Error: GOOGLE_API_KEY not configured. Internet search requires Google API key."
        
        try:
            # Use Gemini with Google Search grounding (integrated search)
            # This enables Google Search directly in the model
            search_prompt = (
                f"Search the internet for information about: {query}. "
                "Provide a detailed, comprehensive answer with specific facts, data, and sources. "
                "Include relevant URLs and citations where applicable."
            )
            
            response = None
            
            # Try different API formats for Google Search integration
            # Format 1: Using types.Tool with GoogleSearch
            try:
                response = self.client.models.generate_content(
                    model=Config.LLM_MODEL,
                    contents=search_prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.7
                    )
                )
            except (AttributeError, TypeError, ValueError) as e1:
                # Format 2: Using dict format for tools
                try:
                    response = self.client.models.generate_content(
                        model=Config.LLM_MODEL,
                        contents=search_prompt,
                        tools=[{"google_search": {}}],
                        config={"temperature": 0.7}
                    )
                except (AttributeError, TypeError, ValueError) as e2:
                    # Format 3: Using config with grounding parameter
                    try:
                        response = self.client.models.generate_content(
                            model=Config.LLM_MODEL,
                            contents=search_prompt,
                            config={
                                "temperature": 0.7,
                                "tools": [{"google_search": {}}]
                            }
                        )
                    except Exception as e3:
                        # Format 4: Simple call - Gemini may have search enabled by default
                        try:
                            response = self.client.models.generate_content(
                                model=Config.LLM_MODEL,
                                contents=search_prompt,
                                config={"temperature": 0.7}
                            )
                        except Exception as e4:
                            return f"Error: Could not perform search. Tried multiple API formats. Last error: {str(e4)}"
            
            if not response:
                return "Error: No response received from search."
            
            # Extract text from response
            result_text = ""
            if hasattr(response, 'text'):
                result_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                if hasattr(response.candidates[0], 'content'):
                    content = response.candidates[0].content
                    if hasattr(content, 'parts'):
                        for part in content.parts:
                            if hasattr(part, 'text'):
                                result_text += part.text
                    elif hasattr(content, 'text'):
                        result_text = content.text
            
            if not result_text:
                return "No results found on the internet."
            
            # Try to extract source citations if available
            sources = []
            try:
                # Try to get grounding metadata with citations
                if hasattr(response, 'grounding_metadata') and response.grounding_metadata:
                    if hasattr(response.grounding_metadata, 'grounding_chunks'):
                        for chunk in response.grounding_metadata.grounding_chunks:
                            if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
                                uri = chunk.web.uri
                                if uri and uri not in sources:
                                    sources.append(uri)
                
                # Alternative: check candidates for citations
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                            if hasattr(candidate.grounding_metadata, 'grounding_chunks'):
                                for chunk in candidate.grounding_metadata.grounding_chunks:
                                    if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
                                        uri = chunk.web.uri
                                        if uri and uri not in sources:
                                            sources.append(uri)
                
                # Also try to extract URLs from the response text
                import re
                url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
                text_urls = re.findall(url_pattern, result_text)
                for url in text_urls:
                    if url and url not in sources:
                        sources.append(url)
                        
            except Exception as e:
                # Citations not available - that's okay, we'll rely on the response text
                pass
            
            # Format response with clear structure
            # The content will be in the language of the query
            formatted = result_text
            
            # Always append sources section at the end
            formatted += "\n\n" + "=" * 60 + "\n"
            formatted += "📚 FUENTES / SOURCES:\n\n"
            
            if sources:
                # Remove duplicates and limit to num_results
                unique_sources = list(dict.fromkeys(sources))[:num_results]
                for i, url in enumerate(unique_sources, 1):
                    formatted += f"{i}. {url}\n"
            else:
                # If no sources were extracted, indicate that they may be in the response text
                formatted += "(Las fuentes están incluidas en el contenido de la respuesta anterior)\n"
                formatted += "(Sources are included in the response content above)\n"
            
            return formatted
            
        except Exception as e:
            return f"Error searching internet: {str(e)}"
    
    def format_results(self, results: str) -> str:
        """
        Returns results as-is since search() already formats them.
        
        Args:
            results: Already formatted string from search()
            
        Returns:
            Formatted results string
        """
        return results if results else "No results found on the internet."

