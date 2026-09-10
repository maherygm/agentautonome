"""Exécution shell restreinte (whitelist de commandes)."""
from __future__ import annotations

import shlex
import subprocess

from .files import get_root

# Whitelist stricte — élargis au fur et à mesure
ALLOWED = {
    "ls",
    "dir",
    "pwd",
    "git",
    "pytest",
    "python",
    "python3",
}


def run_shell(command: str) -> str:
    """Exécute une commande whitelistée dans la racine du projet.

    Args:
        command: Ligne de commande (premier token = binaire autorisé).

    Returns:
        ``exit=CODE`` + stdout/stderr (tronqué), ou message d'erreur.
    """
    parts = shlex.split(command, posix=True)
    if not parts:
        return "ERREUR: commande vide"
    if parts[0] not in ALLOWED:
        return f"ERREUR: '{parts[0]}' non autorisé. Autorisés: {sorted(ALLOWED)}"

    try:
        proc = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(get_root()),
        )
    except subprocess.TimeoutExpired:
        return "ERREUR: timeout (30s)"

    out = (proc.stdout or "") + (proc.stderr or "")
    out = out.strip() or "(aucune sortie)"
    return f"exit={proc.returncode}\n{out[:4000]}"
