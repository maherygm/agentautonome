"""Mémoire de conversation pour la boucle agent (fenêtre glissante)."""
from __future__ import annotations

import json


class Memory:
    """Historique user / assistant / observations envoyé au LLM."""

    def __init__(self, system: str, max_messages: int = 12):
        """
        Args:
            system: Prompt système.
            max_messages: Nombre max de messages conservés (hors system).
        """
        self.system = system
        self.max_messages = max_messages
        self.messages: list[dict] = []

    def add_user(self, content: str) -> None:
        """Ajoute un message utilisateur."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, decision: dict) -> None:
        """Ajoute la décision JSON de l'assistant."""
        self.messages.append(
            {"role": "assistant", "content": json.dumps(decision, ensure_ascii=False)}
        )

    def add_observation(self, obs: str) -> None:
        """Ajoute le résultat d'un outil comme message utilisateur."""
        self.messages.append({"role": "user", "content": f"Observation:\n{obs}"})

    def for_llm(self) -> list[dict]:
        """Construit la liste de messages (system + fenêtre récente)."""
        body = self.messages
        if len(body) > self.max_messages:
            body = body[-self.max_messages :]
        return [{"role": "system", "content": self.system}, *body]
