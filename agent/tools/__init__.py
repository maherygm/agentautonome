"""Registre des outils exposés à la boucle agent."""
from .files import list_dir, read_file, write_file
from .shell import run_shell
from .web import fetch_url, web_search

# Nom d'action JSON -> callable(args: dict) -> str (observation)
REGISTRY = {
    "list_dir": lambda a: list_dir(a.get("path", ".")),
    "read_file": lambda a: read_file(a["path"]),
    "write_file": lambda a: write_file(a["path"], a.get("content", "")),
    "run_shell": lambda a: run_shell(a["command"]),
    "web_search": lambda a: web_search(
        a["query"], a.get("max_results", 5)
    ),
    "fetch_url": lambda a: fetch_url(a["url"]),
}
