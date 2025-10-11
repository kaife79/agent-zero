from __future__ import annotations

import re
import time
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _safe_filename(name: str) -> str:
    name = re.sub(r"https?://", "", name)
    name = re.sub(r"[^a-zA-Z0-9._/-]+", "_", name)
    name = name.strip("/_")
    if not name:
        name = "index"
    return name


def _hostname_dir(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.replace(":", "_")


def create_session(headers: Optional[dict] = None, timeout: int = 20) -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    if headers:
        session.headers.update(headers)
    session.request_timeout = timeout  # type: ignore[attr-defined]
    return session


def fetch_url(
    session: requests.Session,
    url: str,
    *,
    retries: int = 3,
    backoff: float = 1.5,
    save_dir: Optional[str] = None,
) -> Tuple[bytes, Optional[str]]:
    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=getattr(session, "request_timeout", 20))
            resp.raise_for_status()
            content = resp.content
            saved_path: Optional[str] = None
            if save_dir:
                host_dir = _hostname_dir(url)
                # Compose a deterministic filename
                path_part = _safe_filename(url)
                if not path_part.endswith(".html"):
                    path_part += ".html"
                saved_path = f"{save_dir}/{host_dir}/{path_part}"
                # Ensure dirs
                import os

                os.makedirs(os.path.dirname(saved_path), exist_ok=True)
                with open(saved_path, "wb") as f:
                    f.write(content)
            return content, saved_path
        except Exception as exc:  # noqa: BLE001 - network variability expected
            last_exc = exc
            time.sleep(backoff * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def get_soup(html: bytes) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")
