"""
NEXUS Playwright Browser Automation Tool.
Controls headless Chromium to render web pages, scrape dynamic SPAs, take screenshots, and interact with elements.
"""

from typing import Optional
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

class PlaywrightBrowser:
    name = "browser"
    description = "Browse dynamic web pages, take screenshots, click elements, fill forms, and scrape live content"

    async def run(self, action: str = "navigate", **kwargs) -> str:
        """Universal dispatcher for the browser tool."""
        actions = {
            "navigate": self.navigate,
            "open": self.navigate,
            "screenshot": self.screenshot,
            "click": self.click,
            "fill": self.fill,
            "scrape_text": self.scrape_text,
        }
        handler = actions.get(action)
        if not handler:
            if "url" in kwargs:
                return await self.navigate(kwargs["url"])
            return f"[ERROR] Action '{action}' không hợp lệ. Hỗ trợ: {list(actions.keys())}"
        return await handler(**kwargs)

    async def navigate(self, url: str) -> str:
        """Navigate to URL and extract page body text."""
        if not async_playwright:
            return "[ERROR] Thư viện Playwright chưa được cài đặt."
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                title = await page.title()
                text = await page.inner_text("body")
                await browser.close()

                truncated = text[:4000] if len(text) > 4000 else text
                return f"=== TRANG WEB: {title} ({url}) ===\n\n{truncated.strip()}"
        except Exception as e:
            return f"[ERROR] Lỗi khi điều hướng tới {url}: {str(e)}"

    async def screenshot(self, url: str, save_path: str = "screenshot.png") -> str:
        """Navigate to URL and take a full-page screenshot."""
        if not async_playwright:
            return "[ERROR] Thư viện Playwright chưa được cài đặt."
        try:
            target = Path(save_path).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_viewport_size({"width": 1280, "height": 800})
                await page.goto(url, timeout=30000, wait_until="networkidle")
                await page.screenshot(path=str(target), full_page=True)
                await browser.close()
                return f"[SUCCESS] Đã chụp ảnh màn hình và lưu tại: {target}"
        except Exception as e:
            return f"[ERROR] Lỗi khi chụp ảnh {url}: {str(e)}"

    async def click(self, url: str, selector: str) -> str:
        """Navigate to URL and click an element matching selector."""
        if not async_playwright:
            return "[ERROR] Thư viện Playwright chưa được cài đặt."
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                await page.click(selector, timeout=10000)
                page_text = await page.inner_text("body")
                await browser.close()
                return f"[SUCCESS] Đã click '{selector}'. Nội dung mới:\n{page_text[:1500]}"
        except Exception as e:
            return f"[ERROR] Lỗi khi click '{selector}': {str(e)}"

    async def fill(self, url: str, selector: str, text: str) -> str:
        """Navigate to URL, fill an input field, and return status."""
        if not async_playwright:
            return "[ERROR] Thư viện Playwright chưa được cài đặt."
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                await page.fill(selector, text, timeout=10000)
                await browser.close()
                return f"[SUCCESS] Đã điền '{text}' vào selector '{selector}' trên {url}"
        except Exception as e:
            return f"[ERROR] Lỗi khi điền form '{selector}': {str(e)}"

    async def scrape_text(self, url: str, selector: str = "body") -> str:
        """Extract text from a specific CSS selector."""
        if not async_playwright:
            return "[ERROR] Thư viện Playwright chưa được cài đặt."
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                element = await page.wait_for_selector(selector, timeout=15000)
                content = await element.inner_text() if element else ""
                await browser.close()
                return f"=== KẾT QUẢ SCRAPE TỪ {selector} TRÊN {url} ===\n\n{content.strip()}"
        except Exception as e:
            return f"[ERROR] Lỗi khi scrape selector '{selector}' trên {url}: {str(e)}"
