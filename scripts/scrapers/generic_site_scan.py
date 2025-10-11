from __future__ import annotations

import queue
import re
from typing import Iterable, List, Optional, Set

import pandas as pd
from bs4 import BeautifulSoup

from scripts.common.http import create_session, fetch_url, get_soup
from scripts.common.io import PropertyRecord, write_csv


def _normalize_url(base: str, href: str) -> Optional[str]:
    if not href or href.startswith("#"):
        return None
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        # Derive scheme+host from base
        from urllib.parse import urlparse

        p = urlparse(base)
        return f"{p.scheme}://{p.netloc}{href}"
    return base.rstrip("/") + "/" + href.lstrip("/")


def parse_properties_from_html(html: bytes, source_url: str) -> List[PropertyRecord]:
    soup = get_soup(html)
    records: List[PropertyRecord] = []

    # Parse any table that looks like properties
    for table in soup.find_all("table"):
        headers = [h.get_text(strip=True).lower() for h in table.find_all(["th", "td"], limit=10)]
        header_row = table.find("tr")
        if not header_row:
            continue
        ths = [th.get_text(strip=True).lower() for th in header_row.find_all("th")]
        columns = ths if ths else headers
        if not columns:
            continue
        joined = "|".join(columns)
        if not re.search(r"property|waqf|wakf|area|address|purpose|lease|rent", joined):
            continue

        for tr in table.find_all("tr"):
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(tds) < 2:
                continue

            col_map = {c: i for i, c in enumerate(columns)}

            def gv(*names: str) -> Optional[str]:
                for n in names:
                    for k, i in col_map.items():
                        if n in k:
                            if i < len(tds):
                                return tds[i]
                return None

            rec = PropertyRecord(
                source=source_url,
                state=gv("state"),
                property_id=gv("id", "waqf id", "property id"),
                property_name=gv("name", "property"),
                address=gv("address", "location"),
                latitude=None,
                longitude=None,
                area=gv("area", "size"),
                property_type=gv("type", "category"),
                assigned_purpose=gv("purpose", "usage", "use"),
                lease_value=gv("lease", "rent"),
                market_value=gv("market", "circle rate"),
                notes=None,
            )

            if any([
                rec.property_id,
                rec.property_name,
                rec.address,
                rec.area,
                rec.assigned_purpose,
                rec.lease_value,
                rec.market_value,
            ]):
                records.append(rec)

    return records


def scan_sites(
    base_urls: Iterable[str],
    *,
    output_csv: str,
    max_pages: int = 50,
    max_depth: int = 2,
) -> int:
    session = create_session()
    visited: Set[str] = set()
    q: "queue.Queue[tuple[str, int]]" = queue.Queue()

    for url in base_urls:
        q.put((url, 0))

    all_records: List[PropertyRecord] = []

    while not q.empty() and len(visited) < max_pages:
        url, depth = q.get()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        try:
            content, _ = fetch_url(session, url, save_dir="/workspace/data/raw")
        except Exception:
            continue

        all_records.extend(parse_properties_from_html(content, source_url=url))

        # enqueue links
        soup = BeautifulSoup(content, "lxml")
        for a in soup.find_all("a", href=True):
            nxt = _normalize_url(url, a["href"].strip())
            if nxt and nxt not in visited and any(
                k in nxt.lower() for k in [
                    "waqf",
                    "wakf",
                    "property",
                    "lease",
                    "asset",
                    "document",
                    "publication",
                    "list",
                    "download",
                ]
            ):
                q.put((nxt, depth + 1))

    write_csv(output_csv, [r.to_row() for r in all_records])
    return len(all_records)
