"""Outils fichiers sandboxés sous une racine de projet."""
from __future__ import annotations

from pathlib import Path

_ROOT: Path | None = None


def set_root(root: Path) -> None:
    """Définit la racine de travail (tous les chemins y sont relatifs)."""
    global _ROOT
    _ROOT = root.resolve()


def get_root() -> Path:
    """Retourne la racine courante (cwd si non définie)."""
    return (_ROOT or Path.cwd()).resolve()


def _safe(rel: str) -> Path:
    """Résout un chemin relatif en refusant toute sortie de la racine."""
    root = get_root()
    p = (root / rel).resolve()
    try:
        p.relative_to(root)
    except ValueError as e:
        raise ValueError(f"Chemin hors racine: {rel}") from e
    return p


def list_dir(path: str = ".") -> str:
    """Liste le contenu d'un dossier (noms, dossiers avec ``/``)."""
    p = _safe(path)
    if not p.is_dir():
        return f"ERREUR: pas un dossier: {path}"
    items = sorted(x.name + ("/" if x.is_dir() else "") for x in p.iterdir())
    return "\n".join(items) or "(vide)"


def read_file(path: str) -> str:
    """Lit un fichier texte (tronqué à 8000 caractères)."""
    p = _safe(path)
    if not p.is_file():
        return f"ERREUR: fichier introuvable: {path}"
    text = p.read_text(encoding="utf-8", errors="replace")
    return text[:8000] + ("\n...[tronqué]" if len(text) > 8000 else "")


def write_file(path: str, content: str = "") -> str:
    """Écrit un fichier sous la racine (crée les dossiers parents)."""
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"OK écrit {path} ({len(content)} chars)"
