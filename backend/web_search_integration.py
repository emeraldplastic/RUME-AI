"""
Web search integration for Ruma AI Assistant.
Provides intelligent web search capabilities with result summarization.
"""

import asyncio
import json
import logging
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from urllib.parse import quote, urlparse
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Represents a single web search result."""
    title: str
    url: str
    snippet: str
    source: str
    relevance_score: float = 0.0
    timestamp: float = 0.0

@dataclass
class WebSearchConfig:
    """Configuration for web search integration."""
    max_results: int = 10
    timeout: float = 10.0
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1 hour
    safe_search: bool = True

class WebSearchIntegration:
    """Intelligent web search with result processing and summarization."""
    
    def __init__(self, config: Optional[WebSearchConfig] = None):
        self.config = config or WebSearchConfig()
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Search engine configurations
        self.search_engines = {
            "duckduckgo": {
                "url": "https://html.duckduckgo.com/html/",
                "params": {"q": "{query}", "kl": "us-en"}
            },
            "bing": {
                "url": "https://www.bing.com/search",
                "params": {"q": "{query}", "setlang": "en"}
            }
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers={"User-Agent": self.config.user_agent}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def search(self, query: str, engine: str = "duckduckgo") -> List[SearchResult]:
        """Perform web search and return results."""
        # Check cache first
        cache_key = f"{engine}:{query}"
        if self.config.enable_cache and cache_key in self.cache:
            cached = self.cache[cache_key]
            if (asyncio.get_event_loop().time() - cached["timestamp"]) < self.config.cache_ttl:
                logger.info(f"Returning cached results for: {query}")
                return cached["results"]
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            # Perform search
            if engine == "duckduckgo":
                results = await self._search_duckduckgo(query)
            elif engine == "bing":
                results = await self._search_bing(query)
            else:
                raise ValueError(f"Unsupported search engine: {engine}")
            
            # Limit results
            results = results[:self.config.max_results]
            
            # Cache results
            if self.config.enable_cache:
                self.cache[cache_key] = {
                    "results": results,
                    "timestamp": asyncio.get_event_loop().time()
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    async def _search_duckduckgo(self, query: str) -> List[SearchResult]:
        """Search using DuckDuckGo."""
        engine_config = self.search_engines["duckduckgo"]
        params = {k: v.format(query=query) for k, v in engine_config["params"].items()}
        
        async with self.session.get(engine_config["url"], params=params) as response:
            if response.status != 200:
                raise Exception(f"DuckDuckGo search failed: {response.status}")
            
            html = await response.text()
            return self._parse_duckduckgo_results(html)
    
    async def _search_bing(self, query: str) -> List[SearchResult]:
        """Search using Bing."""
        engine_config = self.search_engines["bing"]
        params = {k: v.format(query=query) for k, v in engine_config["params"].items()}
        
        async with self.session.get(engine_config["url"], params=params) as response:
            if response.status != 200:
                raise Exception(f"Bing search failed: {response.status}")
            
            html = await response.text()
            return self._parse_bing_results(html)
    
    def _parse_duckduckgo_results(self, html: str) -> List[SearchResult]:
        """Parse DuckDuckGo search results."""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find result containers
        result_divs = soup.find_all('div', class_='result')
        
        for div in result_divs[:self.config.max_results * 2]:  # Get more to filter
            try:
                title_elem = div.find('a', class_='result__a')
                snippet_elem = div.find('a', class_='result__snippet')
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                # Filter out non-result links
                if not url or url.startswith('#'):
                    continue
                
                result = SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="duckduckgo",
                    relevance_score=self._calculate_relevance(title, snippet),
                    timestamp=asyncio.get_event_loop().time()
                )
                
                results.append(result)
                
            except Exception as e:
                logger.debug(f"Error parsing result: {e}")
                continue
        
        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:self.config.max_results]
    
    def _parse_bing_results(self, html: str) -> List[SearchResult]:
        """Parse Bing search results."""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find result containers
        result_divs = soup.find_all('li', class_='b_algo')
        
        for div in result_divs[:self.config.max_results * 2]:
            try:
                title_elem = div.find('h2')
                link_elem = title_elem.find('a') if title_elem else None
                snippet_elem = div.find('p')
                
                if not link_elem:
                    continue
                
                title = link_elem.get_text(strip=True)
                url = link_elem.get('href', '')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                if not url:
                    continue
                
                result = SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="bing",
                    relevance_score=self._calculate_relevance(title, snippet),
                    timestamp=asyncio.get_event_loop().time()
                )
                
                results.append(result)
                
            except Exception as e:
                logger.debug(f"Error parsing result: {e}")
                continue
        
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:self.config.max_results]
    
    def _calculate_relevance(self, title: str, snippet: str) -> float:
        """Calculate relevance score for a search result."""
        score = 0.0
        
        # Length factors
        title_length = len(title)
        snippet_length = len(snippet)
        
        # Prefer substantial titles and snippets
        if 10 <= title_length <= 100:
            score += 0.3
        if 50 <= snippet_length <= 300:
            score += 0.3
        
        # Check for common spam indicators
        spam_indicators = ['click here', 'download now', 'free', 'buy now', 'subscribe']
        combined_text = (title + " " + snippet).lower()
        
        for indicator in spam_indicators:
            if indicator in combined_text:
                score -= 0.1
        
        # Prefer results from reputable domains (heuristic)
        reputable_domains = ['.edu', '.gov', '.org', 'wikipedia.org', 'github.com']
        for domain in reputable_domains:
            if domain in (title + snippet).lower():
                score += 0.2
                break
        
        return max(0.0, min(1.0, score))
    
    async def fetch_page_content(self, url: str, max_length: int = 5000) -> Optional[str]:
        """Fetch and extract text content from a URL."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text(separator=' ', strip=True)
                
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text)
                
                # Truncate if needed
                if len(text) > max_length:
                    text = text[:max_length] + "..."
                
                return text
                
        except Exception as e:
            logger.error(f"Error fetching page content: {e}")
            return None
    
    def summarize_results(self, results: List[SearchResult], max_results: int = 5) -> str:
        """Summarize search results into a concise response."""
        if not results:
            return "No search results found."
        
        top_results = results[:max_results]
        summary_parts = []
        
        for i, result in enumerate(top_results, 1):
            summary_parts.append(
                f"{i}. {result.title}\n"
                f"   {result.snippet}\n"
                f"   {result.url}"
            )
        
        summary = "\n\n".join(summary_parts)
        return f"Found {len(results)} results. Top {len(top_results)}:\n\n{summary}"
    
    def clear_cache(self):
        """Clear the search result cache."""
        self.cache.clear()
        logger.info("Search cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "cache_enabled": self.config.enable_cache,
            "cache_ttl": self.config.cache_ttl
        }

async def test_web_search():
    """Test the web search integration."""
    config = WebSearchConfig(max_results=5)
    
    async with WebSearchIntegration(config) as search:
        # Test search
        results = await search.search("artificial intelligence latest developments")
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.title}")
            print(f"   {result.url}")
            print(f"   Relevance: {result.relevance_score:.2f}")
        
        # Test summarization
        print("\n\nSummary:")
        print(search.summarize_results(results))

if __name__ == "__main__":
    asyncio.run(test_web_search())
