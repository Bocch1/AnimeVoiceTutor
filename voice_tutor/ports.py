"""Local WebUI port selection shared by the app and smoke-test client."""
import os


def web_port() -> int:
    value = os.environ.get("AVT_WEB_PORT", "8767").strip()
    if not value.isascii() or not value.isdecimal():
        raise ValueError("AVT_WEB_PORT must be a decimal integer between 1024 and 65535")
    port = int(value)
    if not 1024 <= port <= 65535:
        raise ValueError("AVT_WEB_PORT must be between 1024 and 65535")
    if port in (8766, 9880):
        raise ValueError("AVT_WEB_PORT conflicts with the reserved ASR/TTS service port")
    return port
