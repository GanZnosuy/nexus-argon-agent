"""
NEXUS Text-to-Speech (TTS) Engine.
Supports ultra-fast high-quality Edge-TTS (Vietnamese & English voices)
and high-fidelity ElevenLabs voice synthesis.
"""

import os
from pathlib import Path
from typing import Optional
import aiohttp
import config

try:
    import edge_tts
except ImportError:
    edge_tts = None

class TTSEngine:
    name = "tts"
    description = "Convert text to speech audio files (supports Edge-TTS and ElevenLabs)"

    async def run(self, action: str = "edge_tts", text: str = "", **kwargs) -> str:
        """Universal dispatcher for TTS engine."""
        target_text = text or kwargs.get("prompt", "")
        if not target_text:
            return "[ERROR] Không có nội dung văn bản để tạo giọng đọc."

        if action in ("elevenlabs", "eleven_labs"):
            return await self.elevenlabs_generate(
                text=target_text,
                voice_id=kwargs.get("voice_id", "21m00Tcm4TlvDq8ikWAM"),
                output=kwargs.get("output", "voice_eleven.mp3")
            )
        else:
            return await self.edge_tts_generate(
                text=target_text,
                voice=kwargs.get("voice", config.DEFAULT_VOICE),
                rate=kwargs.get("rate", config.DEFAULT_TTS_RATE),
                output=kwargs.get("output", "voice.mp3")
            )

    async def edge_tts_generate(
        self,
        text: str,
        voice: str = "vi-VN-NamMinhNeural",
        rate: str = "+18%",
        output: str = "voice.mp3"
    ) -> str:
        """
        Generate audio using Microsoft Edge-TTS (free, fast, natural).
        Popular voices:
        - vi-VN-NamMinhNeural (Male, Northern)
        - vi-VN-HoaiMyNeural (Female, Northern)
        - en-US-ChristopherNeural (Male, US)
        """
        if not edge_tts:
            return "[ERROR] Thư viện edge-tts chưa được cài đặt."

        try:
            target_path = Path(output).resolve()
            target_path.parent.mkdir(parents=True, exist_ok=True)

            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
            await communicate.save(str(target_path))
            return f"[SUCCESS] Đã tạo âm thanh TTS thành công: {target_path} (Voice: {voice}, Rate: {rate})"
        except Exception as e:
            return f"[ERROR] Lỗi khi tạo âm thanh Edge-TTS: {str(e)}"

    async def elevenlabs_generate(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        output: str = "voice_eleven.mp3"
    ) -> str:
        """
        Generate audio using ElevenLabs API.
        Falls back to Edge-TTS if ELEVENLABS_API_KEY is not configured.
        """
        api_key = config.ELEVENLABS_API_KEY
        if not api_key:
            fallback_res = await self.edge_tts_generate(text=text, output=output)
            return f"[INFO] ELEVENLABS_API_KEY không có trong .env -> Tự động chuyển Edge-TTS.\n{fallback_res}"

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        try:
            target_path = Path(output).resolve()
            target_path.parent.mkdir(parents=True, exist_ok=True)

            timeout = aiohttp.ClientTimeout(total=45)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        err_text = await resp.text()
                        return f"[ERROR] ElevenLabs API error {resp.status}: {err_text}"
                    audio_data = await resp.read()

            with open(target_path, "wb") as f:
                f.write(audio_data)

            return f"[SUCCESS] Đã tạo âm thanh ElevenLabs thành công: {target_path}"
        except Exception as e:
            return f"[ERROR] Lỗi kết nối ElevenLabs: {str(e)}"
