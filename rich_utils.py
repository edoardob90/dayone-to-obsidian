"""Utility module for rich"""
from functools import partial

from rich.console import Console
from rich.progress import Progress

# Default console
console = Console()

# A progress bar
progress = Progress(console=console)

# Print utils: info, warning, verbose
def console_print(message: str, _type: str):
    """Print text with rich"""
    if _type == "warn":
        console.print(f":warning-emoji:  [b][yellow]{message}[/b][/yellow]")
    elif _type == "verbose":
        console.print(f":exclamation: [b][red]{message}[/red][/b]")
    elif _type == "info":
        console.print(f":information_source: {message}")
    else:
        console.print(message)


info_msg = partial(console_print, _type="info")
warn_msg = partial(console_print, _type="warn")
verbose_msg = partial(console_print, _type="verbose")
