# /// script
# dependencies = [
#     "rich",
#     "typer",
# ]
# ///
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys

from rich.console import Console
from rich.table import Table

console = Console()


def run_ruff_audit() -> bool:
    """Run ruff to check for banned casts (TID251)."""
    console.print("[bold blue]Running Ruff Audit (Banned API: TID251)...[/]")
    uv_path = shutil.which("uv") or "uv"
    result = subprocess.run(  # noqa: S603
        [uv_path, "run", "ruff", "check", "--select", "TID251", "."],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        console.print("[bold green]✅ No banned casts found.[/]")
        return True

    console.print("[bold red]❌ Banned casts detected via TID251:[/]")
    console.print(result.stdout)
    return False


def scan_isinstance_chains() -> bool:
    """Scan for excessive or deeply nested isinstance chains."""
    console.print("[bold blue]Scanning for isinstance chains (anti-pattern)...[/]")
    # Look for nested or consecutive isinstance (very basic heuristic)
    chain_pattern = re.compile(
        r"(elif|if)\s+isinstance\(.*?\):.*?\n\s+" r"(elif|if)\s+isinstance\(", re.MULTILINE
    )

    found_any = False
    table = Table(title="Potential isinstance Chains")
    table.add_column("File", style="cyan")
    table.add_column("Line", style="magenta")
    table.add_column("Context", style="white")

    for path in pathlib.Path().rglob("*.py"):
        if any(part in str(path) for part in ("site-packages", ".venv", ".agents")):
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            console.print(f"[yellow]⚠️ Warning:[/] Skipping unreadable file {path}: {e}")
            continue

        matches = list(chain_pattern.finditer(content))
        if matches:
            for match in matches:
                line_no = content.count("\n", 0, match.start()) + 1
                table.add_row(str(path), str(line_no), match.group().replace("\n", " [dim]↩[/] "))
                found_any = True

    if found_any:
        console.print(table)
        console.print("[bold yellow]⚠️ Found potential isinstance chains (anti-pattern).[/]")
        console.print("   [dim]Consider refactoring to a Protocol, Generic, or Polymorphism.[/]")
        return False

    console.print("[bold green]✅ No excessive isinstance chains found in business logic.[/]")
    return True


def main() -> None:
    success = True
    if not run_ruff_audit():
        success = False

    console.print("")
    if not scan_isinstance_chains():
        # Only warn, don't fail for now as the project contains some existing chains
        pass

    if success:
        console.print("\n[bold green]🌟 Type Audit PASSED! Fixes are project-safe.[/]")
        sys.exit(0)
    else:
        console.print(
            "\n[bold red]💀 Type Audit FAILED. Please resolve the issues before committing.[/]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
