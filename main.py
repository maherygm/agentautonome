#!/usr/bin/env python3
"""Point d'entrée CLI de l'agent autonome local (Ollama)."""
from __future__ import annotations

import argparse
from pathlib import Path

from agent.loop import run_agent
from agent import llm as ollama_llm


def main() -> None:
    """Parse les arguments et lance la boucle agent sur l'objectif donné."""
    parser = argparse.ArgumentParser(description="Agent autonome local (Ollama)")
    parser.add_argument("goal", nargs="+", help="Objectif en langage naturel")
    parser.add_argument("--steps", type=int, default=8, help="Budget d'étapes")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--model",
        default=None,
        help="Modèle Ollama (défaut: OLLAMA_MODEL ou qwen2.5:7b)",
    )
    args = parser.parse_args()

    if args.model:
        ollama_llm.MODEL = args.model

    goal = " ".join(args.goal)
    run_agent(goal, project_root=args.root.resolve(), max_steps=args.steps)


if __name__ == "__main__":
    main()
