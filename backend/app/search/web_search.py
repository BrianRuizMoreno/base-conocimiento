"""Web search integration using Tavily API."""

import logging
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"


async def search_web(query: str, max_results: int = 5, search_depth: str = "basic") -> list[dict]:
    """Search the web using Tavily API.
    
    Args:
        query: Search query
        max_results: Maximum number of results (1-10)
        search_depth: "basic" or "advanced"
        
    Returns:
        List of search results with title, url, content, score
    """
    api_key = settings.TAVILY_API_KEY
    if not api_key:
        logger.warning("TAVILY_API_KEY not configured")
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TAVILY_API_URL,
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": search_depth,
                    "include_answer": False,
                    "include_images": False,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            formatted = []
            for r in results:
                formatted.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0),
                })
            
            logger.info(f"Tavily search returned {len(formatted)} results for query: {query[:50]}...")
            return formatted
    except httpx.HTTPStatusError as e:
        logger.error(f"Tavily API error: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []


def format_web_results(results: list[dict]) -> str:
    """Format web search results into context text."""
    if not results:
        return ""
    
    lines = ["--- RESULTADOS DE BUSQUEDA EN INTERNET ---"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}\nURL: {r['url']}\n{r['content']}")
    lines.append("--- FIN RESULTADOS ---")
    return "\n\n".join(lines)
