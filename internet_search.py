"""
Internet search tool as fallback.
Supports multiple APIs: Serper, Bing, Google Custom Search.
"""
import os
import requests
from typing import List, Dict, Optional
from urllib.parse import quote

from config import Config


class InternetSearch:
    """Internet searcher with multiple providers."""
    
    def __init__(self):
        """Initializes the searcher according to configuration."""
        self.api_type = Config.SEARCH_API
        self.api_key = self._get_api_key()
        
    def _get_api_key(self) -> Optional[str]:
        """Gets the API key according to the configured search type."""
        if self.api_type == "serper":
            return Config.SERPER_API_KEY
        elif self.api_type == "bing":
            return Config.BING_API_KEY
        elif self.api_type == "google":
            return Config.GOOGLE_API_KEY
        return None
    
    def search_serper(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search using Serper API."""
        if not self.api_key:
            raise ValueError("SERPER_API_KEY not configured in environment variables")
        
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": num_results
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "source": "Serper"
                })
            
            return results
        except Exception as e:
            print(f"❌ Error in Serper search: {e}")
            return []
    
    def search_bing(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search using Bing Search API."""
        if not self.api_key:
            raise ValueError("BING_API_KEY not configured in environment variables")
        
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key
        }
        params = {
            "q": query,
            "count": num_results,
            "textDecorations": False,
            "textFormat": "Raw"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("webPages", {}).get("value", []):
                results.append({
                    "title": item.get("name", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("url", ""),
                    "source": "Bing"
                })
            
            return results
        except Exception as e:
            print(f"❌ Error in Bing search: {e}")
            return []
    
    def search_google_custom(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search using Google Custom Search API."""
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not configured")
        if not Config.GOOGLE_SEARCH_ENGINE_ID:
            raise ValueError("GOOGLE_SEARCH_ENGINE_ID not configured")
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.api_key,
            "cx": Config.GOOGLE_SEARCH_ENGINE_ID,
            "q": query,
            "num": min(num_results, 10)  # Google limita a 10
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("items", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "source": "Google Custom Search"
                })
            
            return results
        except Exception as e:
            print(f"❌ Error in Google search: {e}")
            return []
    
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Performs internet search according to the configured API.
        Returns a list of results with title, snippet, link and source.
        """
        if not self.api_key:
            # Don't show warning if there's no API key - it's optional
            return []
        
        try:
            if self.api_type == "serper":
                return self.search_serper(query, num_results)
            elif self.api_type == "bing":
                return self.search_bing(query, num_results)
            elif self.api_type == "google":
                return self.search_google_custom(query, num_results)
            else:
                print(f"⚠️ Search type '{self.api_type}' not supported")
                return []
        except Exception as e:
            print(f"❌ Error in search: {e}")
            return []
    
    def format_results(self, results: List[Dict]) -> str:
        """Formats search results as readable text."""
        if not results:
            return "No results found on the internet."
        
        formatted = "Internet search results:\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. {result['title']}\n"
            formatted += f"   {result['snippet']}\n"
            formatted += f"   Source: {result['link']}\n\n"
        
        return formatted

