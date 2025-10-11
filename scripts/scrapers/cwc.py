from __future__ import annotations

import re
from typing import List, Optional

import pandas as pd
from bs4 import BeautifulSoup

from scripts.common.http import create_session, fetch_url, get_soup
from scripts.common.io import PropertyRecord, write_csv


BASE = "https://centralwaqfcouncil.gov.in/"


def parse_table(soup: BeautifulSoup) -> List[PropertyRecord]:
    records: List[PropertyRecord] = []

    # Try to find any table that resembles property listings; CWC site varies.
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
        if not re.search(r"property|waqf|area|address|purpose|lease", joined):
            continue

        for tr in table.find_all("tr"):
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(tds) < 2:
                continue
            # Try to map common column names
            col_map = {c: i for i, c in enumerate(columns)}
            def gv(*names: str) -> Optional[str]:
                for n in names:
                    for k, i in col_map.items():
                        if n in k:
                            if i < len(tds):
                                return tds[i]
                return None

            prop_id = gv("id", "waqf id", "property id")
            prop_name = gv("name", "property")
            address = gv("address", "location")
            area = gv("area", "size")
            purpose = gv("purpose", "usage", "use")
            lease = gv("lease", "rent")
            market = gv("market", "circle rate")

            if not any([prop_id, prop_name, address, area, purpose, lease, market]):
                continue

            rec = PropertyRecord(
                source=BASE,
                state=None,
                property_id=prop_id,
                property_name=prop_name,
                address=address,
                latitude=None,
                longitude=None,
                area=area,
                property_type=None,
                assigned_purpose=purpose,
                lease_value=lease,
                market_value=market,
                notes=None,
            )
            records.append(rec)

    return records


def crawl_cwc(listing_paths: Optional[List[str]] = None) -> List[PropertyRecord]:
    session = create_session()
    entry_urls: List[str] = []
    if listing_paths:
        entry_urls = [p if p.startswith("http") else BASE.rstrip("/") + "/" + p.lstrip("/") for p in listing_paths]
    else:
        # Heuristic paths commonly hosting data or publications
        entry_urls = [
            BASE,
            BASE + "documents",
            BASE + "publication",
            BASE + "sites/default/files/",
        ]

    all_records: List[PropertyRecord] = []
    for url in entry_urls:
        try:
            content, saved = fetch_url(session, url, save_dir="/workspace/data/raw/cwc")
            soup = get_soup(content)
            records = parse_table(soup)
            all_records.extend(records)

            # Follow document links that might be Excel/CSV or HTML
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not href or href.startswith("#"):
                    continue
                if any(href.lower().endswith(ext) for ext in [".xlsx", ".xls", ".csv", ".html", ".htm"]):
                    full = href if href.startswith("http") else BASE.rstrip("/") + "/" + href.lstrip("/")
                    try:
                        bin_content, saved2 = fetch_url(session, full, save_dir="/workspace/data/raw/cwc")
                        if full.lower().endswith(('.html', '.htm')):
                            sub = get_soup(bin_content)
                            all_records.extend(parse_table(sub))
                        elif full.lower().endswith(('.xlsx', '.xls')):
                            try:
                                df = pd.read_excel(bin_content)  # type: ignore[arg-type]
                            except Exception:
                                # If binary path, try reading from saved file
                                if saved2:
                                    df = pd.read_excel(saved2)
                                else:
                                    raise
                            all_records.extend(_records_from_df(df))
                        elif full.lower().endswith('.csv'):
                            try:
                                df = pd.read_csv(full)
                            except Exception:
                                if saved2:
                                    df = pd.read_csv(saved2)
                                else:
                                    raise
                            all_records.extend(_records_from_df(df))
                    except Exception:
                        continue
        except Exception:
            continue

    return all_records


def _records_from_df(df: pd.DataFrame) -> List[PropertyRecord]:
    # Normalize headers
    lower = {str(c).strip().lower(): c for c in df.columns}
    def gv(row, *names: str) -> Optional[str]:
        for n in names:
            for key, orig in lower.items():
                if n in key:
                    val = row.get(orig)
                    if pd.isna(val):
                        continue
                    return str(val)
        return None

    records: List[PropertyRecord] = []
    for _, row in df.iterrows():
        rec = PropertyRecord(
            source=BASE,
            state=gv(row, "state"),
            property_id=gv(row, "id", "waqf id", "property id"),
            property_name=gv(row, "name", "property"),
            address=gv(row, "address", "location"),
            latitude=None,
            longitude=None,
            area=gv(row, "area", "size"),
            property_type=gv(row, "type", "category"),
            assigned_purpose=gv(row, "purpose", "usage", "use"),
            lease_value=gv(row, "lease", "rent"),
            market_value=gv(row, "market", "circle rate"),
            notes=None,
        )
        # Only add if any key data present
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


def main(output_csv: str = "/workspace/data/processed/cwc_properties.csv") -> None:
    records = crawl_cwc()
    write_csv(output_csv, [r.to_row() for r in records])


if __name__ == "__main__":
    main()
