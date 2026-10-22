"""
NEXUS Web Search & Information Retrieval Tool.
Provides web search, YouTube video search, and web page content extraction.
"""

import asyncio
from typing import Optional, List, Dict
import aiohttp
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

class WebSearchTool:
    name = "web_search"
    description = "Search web pages (Google/DDG), YouTube videos, and read article content from URLs"

    async def run(self, action: str = "search", **kwargs) -> str:
        """Universal dispatcher for the tool registry."""
        actions = {
            "search": self.search,
            "google_search": self.search,
            "youtube_search": self.youtube_search,
            "read_url": self.read_url,
        }
        handler = actions.get(action)
        if not handler:
            # Fallback if action is directly passed as query or unrecognized
            if "query" in kwargs:
                return await self.search(kwargs["query"])
            elif "url" in kwargs:
                return await self.read_url(kwargs["url"])
            return f"[ERROR] Action '{action}' không hỗ trợ. Hỗ trợ: {list(actions.keys())}"
        return await handler(**kwargs)

    async def search(self, query: str, max_results: int = 10) -> str:
        """
        Perform a web search and return structured snippets.
        """
        if not query:
            return "[ERROR] Không có từ khóa tìm kiếm."

        def _sync_search():
            if not DDGS:
                return "[ERROR] Thư viện tìm kiếm ddgs/duckduckgo_search chưa được cài đặt."
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
                if not results:
                    return f"[INFO] Không tìm thấy kết quả nào cho: '{query}'"

                output = [f"=== KẾT QUẢ TÌM KIẾM CHO: '{query}' ==="]
                for i, r in enumerate(results, 1):
                    title = r.get("title", "Không có tiêu đề")
                    link = r.get("href", "")
                    snippet = r.get("body", "")
                    output.append(f"{i}. [bold]{title}[/]\n   Link: {link}\n   Trích đoạn: {snippet}\n")
                return "\n".join(output)
            except Exception as e:
                return f"[ERROR] Lỗi khi tìm kiếm web: {str(e)}"

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_search)

    async def google_search(self, query: str, max_results: int = 10) -> str:
        """Alias for search."""
        return await self.search(query=query, max_results=max_results)

    async def youtube_search(self, query: str, max_results: int = 5) -> str:
        """
        Search for YouTube videos and return metadata.
        """
        if not query:
            return "[ERROR] Không có từ khóa tìm kiếm YouTube."

        def _sync_yt():
            if not DDGS:
                return "[ERROR] Thư viện ddgs chưa được cài đặt."
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.videos(query, max_results=max_results))
                if not results:
                    return f"[INFO] Không tìm thấy video nào cho: '{query}'"

                output = [f"=== VIDEO YOUTUBE CHO: '{query}' ==="]
                for i, r in enumerate(results, 1):
                    title = r.get("title", "")
                    link = r.get("content", "")
                    uploader = r.get("uploader", "Unknown Channel")
                    views = r.get("statistics", {}).get("viewCount", "N/A")
                    duration = r.get("duration", "N/A")
                    desc = r.get("description", "")[:150]
                    output.append(
                        f"{i}. {title}\n"
                        f"   Kênh: {uploader} | Thời lượng: {duration} | Lượt xem: {views}\n"
                        f"   URL: {link}\n"
                        f"   Mô tả: {desc}...\n"
                    )
                return "\n".join(output)
            except Exception as e:
                return f"[ERROR] Lỗi khi tìm kiếm YouTube: {str(e)}"

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_yt)

    async def read_url(self, url: str, max_chars: int = 5000) -> str:
        """
        Fetch HTML from URL, clean boilerplate, and return readable text.
        """
        if not url:
            return "[ERROR] Không có URL để đọc."

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }

        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return f"[ERROR] HTTP Error {resp.status} khi truy cập {url}"
                    html = await resp.text(encoding="utf-8", errors="replace")

            soup = BeautifulSoup(html, "html.parser")
            # Remove scripts, styles, metadata
            for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
                element.decompose()

            text = soup.get_text(separator="\n", strip=True)
            cleaned_lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned_text = "\n".join(cleaned_lines)

            if len(cleaned_text) > max_chars:
                cleaned_text = cleaned_text[:max_chars] + f"\n... [Đã rút gọn vì vượt quá {max_chars} ký tự]"

            return f"=== NỘI DUNG TỪ {url} ===\n\n{cleaned_text}"
        except Exception as e:
            return f"[ERROR] Lỗi khi đọc nội dung từ {url}: {str(e)}"
