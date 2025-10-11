from __future__ import annotations

import typer
from rich import print

from scripts.scrapers.cwc import main as cwc_main

app = typer.Typer(add_completion=False)


@app.command()
def cwc(output_csv: str = "/workspace/data/processed/cwc_properties.csv"):
    print("[bold green]Running Central Waqf Council crawler...[/bold green]")
    cwc_main(output_csv)
    print(f"[bold blue]Saved:[/bold blue] {output_csv}")


if __name__ == "__main__":
    app()
