"""
Shared logging configuration using the rich library.
"""

import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rprint

# Create console for rich output
console = Console()

def setup_logging():
    """Setup rich logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)]
    )
    return logging.getLogger("toronto_streetview_crawler")

def create_progress_bar():
    """Create a progress bar for panorama processing."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
        expand=True
    )

def print_header(title, subtitle=None):
    """Print a beautiful header."""
    header_text = Text(title, style="bold blue")
    if subtitle:
        header_text.append(f"\n{subtitle}", style="dim")
    
    panel = Panel(header_text, border_style="blue")
    console.print(panel)

def print_success(message):
    """Print a success message."""
    console.print(f"✅ {message}", style="green")

def print_error(message):
    """Print an error message."""
    console.print(f"❌ {message}", style="red")

def print_warning(message):
    """Print a warning message."""
    console.print(f"⚠️  {message}", style="yellow")

def print_info(message):
    """Print an info message."""
    console.print(f"ℹ️  {message}", style="blue")

def print_panorama_stats(conn):
    """Print current panorama statistics from database."""
    try:
        total = conn.execute("SELECT COUNT(*) FROM panoramas").fetchone()[0]
        populated = conn.execute("SELECT COUNT(*) FROM panoramas WHERE metadata_populated = 1").fetchone()[0]
        within_boundary = conn.execute("SELECT COUNT(*) FROM panoramas WHERE within_boundary = 1").fetchone()[0]
        expanded = conn.execute("SELECT COUNT(*) FROM panoramas WHERE neighbors_expanded = 1").fetchone()[0]
        
        table = Table(title="Database Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Percentage", style="yellow")
        
        table.add_row("Total Panoramas", str(total), "100%")
        table.add_row("Metadata Populated", str(populated), f"{(populated/total*100):.1f}%" if total > 0 else "0%")
        table.add_row("Within Boundary", str(within_boundary), f"{(within_boundary/total*100):.1f}%" if total > 0 else "0%")
        table.add_row("Neighbors Expanded", str(expanded), f"{(expanded/total*100):.1f}%" if total > 0 else "0%")
        
        console.print(table)
        
        return total, populated, within_boundary, expanded
    except Exception as e:
        console.print(f"Error getting stats: {e}", style="red")
        return 0, 0, 0, 0
