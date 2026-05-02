"""ElevenLabs TTS (Text-to-Speech) wrapper for Talk to Louis.

Converts text responses to speech audio using ElevenLabs API.
Async, with timeout and fallback for robustness.

Usage:
    tts = ElevenLabsWrapper()
    audio_bytes = await tts.synthesize("Hello, how are you?")
"""

import asyncio
import logging
import os
from typing import Optional

try:
    import aiohttp
except ImportError:
    aiohttp = None

logger = logging.getLogger("elevenlabs_wrapper")


class ElevenLabsWrapper:
    """Wrapper for ElevenLabs TTS API."""
    
    # Default voice (female, neutral)
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
    
    # ElevenLabs API endpoint
    API_BASE_URL = "https://api.elevenlabs.io/v1"
    
    # Timeout for API request (seconds)
    API_TIMEOUT = 5.0
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
    ):
        """Initialize ElevenLabs wrapper.
        
        Args:
            api_key: ElevenLabs API key (defaults to ELEVENLABS_API_KEY env var)
            voice_id: Voice ID to use (defaults to DEFAULT_VOICE_ID)
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = voice_id or self.DEFAULT_VOICE_ID
        
        if not self.api_key:
            logger.warning(
                "⚠️ ELEVENLABS_API_KEY not set. "
                "TTS will not work. Set env var or pass api_key to constructor."
            )
    
    async def synthesize(self, text: str) -> bytes:
        """Convert text to speech.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Audio bytes (MP3 format), or empty bytes if API fails/timeout
            
        Note:
            - Returns b"" if API not configured (no exception thrown)
            - Returns b"" on timeout or API error
            - Respects 5-second timeout
        """
        # Guard: if no API key, return empty
        if not self.api_key:
            logger.debug("No ELEVENLABS_API_KEY; returning empty audio")
            return b""
        
        # Guard: empty text
        if not text or not text.strip():
            logger.debug("Empty text; returning empty audio")
            return b""
        
        # Guard: aiohttp not available
        if aiohttp is None:
            logger.error("aiohttp not installed; cannot call ElevenLabs API")
            return b""
        
        # Build request
        url = f"{self.API_BASE_URL}/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }
        
        try:
            # Async request with timeout
            timeout = aiohttp.ClientTimeout(total=self.API_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url, json=payload, headers=headers
                ) as resp:
                    if resp.status == 200:
                        audio_bytes = await resp.read()
                        logger.debug(
                            f"✅ TTS synthesized {len(text)} chars → {len(audio_bytes)} bytes"
                        )
                        return audio_bytes
                    else:
                        error_text = await resp.text()
                        logger.error(
                            f"❌ ElevenLabs API error (status {resp.status}): {error_text}"
                        )
                        return b""
        
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ ElevenLabs API timeout (>{self.API_TIMEOUT}s)")
            return b""
        
        except aiohttp.ClientError as e:
            logger.error(f"❌ ElevenLabs API client error: {e}")
            return b""
        
        except Exception as e:
            logger.error(f"❌ Unexpected error in TTS: {e}")
            return b""
    
    def get_status(self) -> dict:
        """Get wrapper status (for debugging).
        
        Returns:
            Dict with configuration and health status
        """
        return {
            "api_key_configured": bool(self.api_key),
            "voice_id": self.voice_id,
            "api_timeout": self.API_TIMEOUT,
            "aiohttp_available": aiohttp is not None,
        }


# Singleton instance (optional)
_tts_instance: Optional[ElevenLabsWrapper] = None


def get_tts_wrapper() -> ElevenLabsWrapper:
    """Get singleton TTS wrapper instance.
    
    Returns:
        ElevenLabsWrapper instance (lazy-initialized)
    """
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = ElevenLabsWrapper()
    return _tts_instance


# For quick testing
if __name__ == "__main__":
    import asyncio
    
    async def test():
        wrapper = ElevenLabsWrapper()
        status = wrapper.get_status()
        print(f"TTS Status: {status}\n")
        
        test_text = "Congratulations on completing your eye screening. Your results will be reviewed by a specialist."
        
        print(f"Synthesizing: {test_text!r}\n")
        audio = await wrapper.synthesize(test_text)
        
        if audio:
            print(f"✅ Success! Received {len(audio)} bytes of audio")
        else:
            print("❌ Failed or no audio returned (API not configured?)")
    
    asyncio.run(test())
