"""
NEXUS YouTube API Tool.
Wrapper for YouTube Data API v3: video listing, analytics, metadata updates, and upload workflows.
"""

import os
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
import config

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    build = None
    HttpError = Exception

class YouTubeAPITool:
    name = "youtube_api"
    description = "Manage YouTube channel videos, query statistics, view counts, and update video metadata"

    def __init__(self):
        self.api_key = config.YOUTUBE_API_KEY

    def _get_service(self):
        """Construct YouTube Data API client service."""
        if not build:
            raise RuntimeError("Thư viện google-api-python-client chưa được cài đặt.")
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY chưa được cấu hình trong .env.")
        return build("youtube", "v3", developerKey=self.api_key)

    async def run(self, action: str = "get_analytics", **kwargs) -> str:
        """Universal dispatcher for YouTube API operations."""
        actions = {
            "get_analytics": self.get_analytics,
            "get_stats": self.get_analytics,
            "list_videos": self.list_videos,
            "update_metadata": self.update_metadata,
            "upload": self.upload,
        }
        handler = actions.get(action)
        if not handler:
            return f"[ERROR] Action '{action}' không hợp lệ. Hỗ trợ: {list(actions.keys())}"
        return await handler(**kwargs)

    async def get_analytics(self, video_id: str, **kwargs) -> str:
        """Fetch statistics (views, likes, comments) for a specific video ID."""
        if not video_id:
            return "[ERROR] Không có video_id để tra cứu số liệu."

        # Clean video_id if full URL was passed
        if "v=" in video_id:
            video_id = video_id.split("v=")[1].split("&")[0]
        elif "youtu.be/" in video_id:
            video_id = video_id.split("youtu.be/")[1].split("?")[0]

        def _sync_stats():
            try:
                service = self._get_service()
                request = service.videos().list(
                    part="snippet,statistics,contentDetails",
                    id=video_id
                )
                response = request.execute()
                items = response.get("items", [])
                if not items:
                    return f"[INFO] Không tìm thấy video YouTube với ID: {video_id}"

                item = items[0]
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})

                title = snippet.get("title", "")
                channel = snippet.get("channelTitle", "")
                views = stats.get("viewCount", "0")
                likes = stats.get("likeCount", "0")
                comments = stats.get("commentCount", "0")

                return (
                    f"=== THỐNG KÊ VIDEO YOUTUBE: {title} ===\n"
                    f"ID: {video_id}\n"
                    f"Kênh: {channel}\n"
                    f"Lượt xem (Views): {int(views):,}\n"
                    f"Lượt thích (Likes): {int(likes):,}\n"
                    f"Bình luận (Comments): {int(comments):,}\n"
                    f"Ngày đăng: {snippet.get('publishedAt', 'N/A')}\n"
                )
            except Exception as e:
                return f"[ERROR khi lấy analytics YouTube]: {str(e)}"

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_stats)

    async def list_videos(self, channel_id: Optional[str] = None, query: str = "", max_results: int = 10, **kwargs) -> str:
        """List videos for a channel or search term."""
        def _sync_list():
            try:
                service = self._get_service()
                params: Dict[str, Any] = {
                    "part": "snippet",
                    "maxResults": max_results,
                    "type": "video"
                }
                if channel_id:
                    params["channelId"] = channel_id
                if query:
                    params["q"] = query

                request = service.search().list(**params)
                response = request.execute()
                items = response.get("items", [])
                if not items:
                    return f"[INFO] Không tìm thấy video nào."

                output = [f"=== DANH SÁCH VIDEO ({len(items)} kết quả) ==="]
                for i, it in enumerate(items, 1):
                    v_id = it.get("id", {}).get("videoId", "")
                    snip = it.get("snippet", {})
                    output.append(f"{i}. {snip.get('title')} (ID: {v_id})\n   Kênh: {snip.get('channelTitle')}\n")
                return "\n".join(output)
            except Exception as e:
                return f"[ERROR khi liệt kê video]: {str(e)}"

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_list)

    async def update_metadata(self, video_id: str, title: Optional[str] = None, description: Optional[str] = None, tags: Optional[List[str]] = None, **kwargs) -> str:
        """Update video title, description, or tags (requires OAuth token with write scope)."""
        return f"[INFO] Để cập nhật metadata video {video_id}, cần OAuth 2.0 Web/Desktop Client Credentials với quyền 'youtube.force-ssl'. API Key chỉ hỗ trợ đọc dữ liệu (Read-only)."

    async def upload(self, file_path: str, title: str, description: str = "", tags: Optional[List[str]] = None, privacy: str = "unlisted", **kwargs) -> str:
        """Upload video to YouTube (requires OAuth client_secrets.json)."""
        target = Path(file_path).resolve()
        if not target.exists():
            return f"[ERROR] Tệp video không tồn tại: {file_path}"
        return (
            f"[INFO] Tệp video sẵn sàng tải lên: {target}\n"
            "Tính năng tải lên tự động (Resumable Upload) yêu cầu file xác thực OAuth `client_secrets.json` của Google Cloud Console để người dùng cấp quyền ghi kênh YouTube."
        )
