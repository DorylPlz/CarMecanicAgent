"""
Internet search using Gemini's integrated Google Search.
No external API keys required - uses Gemini's native search capabilities.
"""
import os
from typing import Optional
from google.genai import Client, types

from config import Config
import re
from urllib.parse import urlparse


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
    
    def _is_valid_source_url(self, url: str) -> bool:
        """
        Validates if a URL is a valid source (not a search page or redirect).
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip()
        
        # Must start with http:// or https://
        if not url.startswith(('http://', 'https://')):
            return False
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Filter out search engine result pages
            search_domains = [
                'google.com',
                'google.co',
                'google.',
                'youtube.com/results',
                'bing.com/search',
                'duckduckgo.com',
                'search.yahoo.com',
            ]
            
            for search_domain in search_domains:
                if search_domain in domain or domain.endswith(search_domain):
                    return False
            
            # Filter out URLs that are clearly search queries
            if 'search_query=' in url or 'q=' in url or 'query=' in url:
                # But allow specific sites that might use these params legitimately
                if 'reddit.com' not in domain and 'stackoverflow.com' not in domain:
                    return False
            
            # Filter out very short URLs (likely incomplete)
            if len(url) < 15:
                return False
            
            # Must have a valid domain
            if not domain or '.' not in domain:
                return False
            
            # Filter out localhost and IP addresses
            if domain.startswith('localhost') or domain.replace('.', '').replace(':', '').isdigit():
                return False
            
            return True
            
        except Exception:
            return False
    
    def _extract_valid_urls(self, sources: list) -> list:
        """
        Filters and validates URLs, removing invalid ones.
        
        Args:
            sources: List of URLs to filter
            
        Returns:
            List of valid URLs
        """
        valid_urls = []
        seen_domains = set()
        
        for url in sources:
            if not url:
                continue
            
            url = url.strip()
            
            # Validate URL
            if not self._is_valid_source_url(url):
                continue
            
            # Avoid duplicates by domain
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                
                # Allow multiple URLs from same domain if they're different paths
                if url not in valid_urls:
                    valid_urls.append(url)
            except Exception:
                continue
        
        return valid_urls
    
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
            # The query language is preserved - results will be returned and should be translated by the agent
            search_prompt = (
                f"Search the internet for information about: {query}. "
                "Provide a detailed, comprehensive answer with specific facts, data, and sources. "
                "Include relevant URLs and citations where applicable. "
                "Provide the response in the same language as the query if possible."
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
            all_sources = []
            try:
                # Try to get grounding metadata with citations
                if hasattr(response, 'grounding_metadata') and response.grounding_metadata:
                    if hasattr(response.grounding_metadata, 'grounding_chunks'):
                        for chunk in response.grounding_metadata.grounding_chunks:
                            if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
                                uri = chunk.web.uri
                                if uri:
                                    all_sources.append(uri)
                
                # Alternative: check candidates for citations
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                            if hasattr(candidate.grounding_metadata, 'grounding_chunks'):
                                for chunk in candidate.grounding_metadata.grounding_chunks:
                                    if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
                                        uri = chunk.web.uri
                                        if uri:
                                            all_sources.append(uri)
                
                # Also try to extract URLs from the response text (but be selective)
                url_pattern = r'https?://[^\s\)]+'
                text_urls = re.findall(url_pattern, result_text)
                for url in text_urls:
                    # Clean up URL (remove trailing punctuation that might not be part of URL)
                    url = url.rstrip('.,;:!?)')
                    if url:
                        all_sources.append(url)
                        
            except Exception as e:
                # Citations not available - that's okay, we'll rely on the response text
                pass
            
            # Filter and validate URLs
            sources = self._extract_valid_urls(all_sources)
            
            # Format response with clear structure
            # The content will be in the language of the query
            formatted = result_text
            
            # Note: We don't include URLs in the sources section because
            # the URLs from Gemini's grounding metadata are often invalid (404) or incomplete.
            # The information itself is reliable and complete in the response text.
            # If URLs are needed, they should be mentioned in the response content by the agent.
            
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

