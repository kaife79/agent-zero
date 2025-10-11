from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich import print

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.scrapers.cwc import main as cwc_main  # noqa: E402
from scripts.scrapers.generic_site_scan import scan_sites  # noqa: E402

app = typer.Typer(add_completion=False)


@app.command()
def cwc(output_csv: str = "/workspace/data/processed/cwc_properties.csv"):
    print("[bold green]Running Central Waqf Council crawler...[/bold green]")
    cwc_main(output_csv)
    print(f"[bold blue]Saved:[/bold blue] {output_csv}")


@app.command()
def scan(
    urls: list[str] = typer.Option(
        [],
        "--url",
        help="Base URLs to scan for property lists",
    ),
    output_csv: str = "/workspace/data/processed/site_scan_properties.csv",
    max_pages: int = 50,
    max_depth: int = 2,
):
    if not urls:
        urls = [
            "https://centralwaqfcouncil.gov.in/",
            "https://waqf.gov.in/",
            "https://delhiwaqfboard.delhi.gov.in/",
            "https://delhiwaqfboard.gov.in/",
            "https://upwaqfboard.gov.in/",
            "https://tswaqfboard.in/",
            "https://karnatakawakfboard.kar.nic.in/",
            "https://keralastatewakfboard.in/",
            "https://maharashtrawaqfboard.in/",
        ]
    print(f"[bold green]Scanning {len(urls)} site(s) up to depth {max_depth}...[/bold green]")
    count = scan_sites(urls, output_csv=output_csv, max_pages=max_pages, max_depth=max_depth)
    print(f"[bold blue]Found records:[/bold blue] {count} -> {output_csv}")


if __name__ == "__main__":
    app()
