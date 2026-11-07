"""In-memory presence of localhost chat tabs for one-click desktop shutdown.

This does not stop the server by itself. Only the optional one-click Windows
launcher runs a watchdog that can close services owned by that launcher.
"""

from __future__ import annotations

import re
from threading import RLock
from time import monotonic

_CLIENT_ID = re.compile(r"^[A-Za-z0-9_-]{8,100}$")


class BrowserPresence:
    def __init__(self, *, expiry_seconds: float = 120.0):
        self.expiry_seconds = expiry_seconds
        self._lock = RLock()
        self._clients: dict[str, float] = {}
        self._ever_connected = False
        self._inactive_since: float | None = None

    def _prune(self, now: float) -> None:
        stale = [key for key, last in self._clients.items() if now - last > self.expiry_seconds]
        for key in stale:
            del self._clients[key]
        if self._ever_connected and not self._clients and self._inactive_since is None:
            self._inactive_since = now

    def ping(self, client_id: str) -> None:
        if not _CLIENT_ID.fullmatch(client_id):
            raise ValueError("Invalid local browser client ID")
        with self._lock:
            now = monotonic()
            self._prune(now)
            if len(self._clients) >= 32 and client_id not in self._clients:
                raise ValueError("Too many browser tabs")
            self._clients[client_id] = now
            self._ever_connected = True
            self._inactive_since = None

    def leave(self, client_id: str) -> None:
        if not _CLIENT_ID.fullmatch(client_id):
            raise ValueError("Invalid local browser client ID")
        with self._lock:
            now = monotonic()
            self._prune(now)
            self._clients.pop(client_id, None)
            if self._ever_connected and not self._clients and self._inactive_since is None:
                self._inactive_since = now

    def status(self) -> dict:
        with self._lock:
            now = monotonic()
            self._prune(now)
            return {
                "ever_connected": self._ever_connected,
                "active_clients": len(self._clients),
                "inactive_seconds": (
                    round(now - self._inactive_since, 2)
                    if self._inactive_since is not None else None
                ),
            }


browser_presence = BrowserPresence()
