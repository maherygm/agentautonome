"""Boucle principale de l'agent : modes Ask / Plan / Agentic et outils."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from .llm import chat, chat_text, ensure_ollama
from .memory import Memory
from .tools import REGISTRY
from .tools.files import set_root

MAX_STEPS = 8
_REPO_ROOT = Path(__file__).resolve().parent.parent

Mode = Literal["ask", "plan", "agentic"]
EventCallback = Callable[[dict[str, Any]], None]

WEB_TOOLS = {"web_search", "fetch_url"}
PLAN_TOOLS = {"list_dir", "read_file", "web_search", "fetch_url"}
PROMPT_FILES = {
    "ask": "ask.md",
    "ask_web": "ask_web.md",
    "plan": "plan.md",
    "agentic": "system.md",
}


def load_system(work_root: Path, mode: Mode = "agentic", *, web_search: bool = True) -> str:
    """Charge le prompt système selon le mode (et Ask+web si besoin).

    Args:
        work_root: Racine de travail injectée dans ``{{ROOT}}``.
        mode: Mode d'exécution.
        web_search: Si vrai en Ask, utilise le prompt avec outils web.

    Returns:
        Texte du prompt système prêt à l'emploi.
    """
    if mode == "ask" and web_search:
        name = PROMPT_FILES["ask_web"]
    else:
        name = PROMPT_FILES.get(mode, "system.md")
    tpl = (_REPO_ROOT / "prompts" / name).read_text(encoding="utf-8")
    return tpl.replace("{{ROOT}}", str(work_root.resolve()))


def _registry_for(mode: Mode, web_search: bool) -> dict:
    """Construit le sous-ensemble d'outils autorisés pour ce mode."""
    if mode == "ask":
        tools = {k: v for k, v in REGISTRY.items() if k in WEB_TOOLS} if web_search else {}
    elif mode == "plan":
        tools = {k: v for k, v in REGISTRY.items() if k in PLAN_TOOLS}
    else:
        tools = dict(REGISTRY)

    if not web_search:
        tools = {k: v for k, v in tools.items() if k not in WEB_TOOLS}
    return tools


def run_agent(
    goal: str,
    *,
    project_root: Path | None = None,
    max_steps: int = MAX_STEPS,
    mode: Mode = "agentic",
    web_search: bool = True,
    on_event: EventCallback | None = None,
) -> str:
    """Exécute l'agent jusqu'à ``finish`` ou épuisement du budget d'étapes.

    Args:
        goal: Objectif en langage naturel.
        project_root: Racine sandbox (cwd par défaut).
        max_steps: Nombre max d'itérations outil.
        mode: ``ask`` | ``plan`` | ``agentic``.
        web_search: Active ``web_search`` / ``fetch_url``.
        on_event: Callback pour chaque événement (step, observation, done, error).

    Returns:
        Message final (finish) ou arrêt sur budget.
    """
    root = (project_root or Path.cwd()).resolve()
    ensure_ollama()
    set_root(root)

    def emit(event: dict[str, Any]) -> None:
        if on_event:
            on_event(event)

    if mode == "ask" and not web_search:
        messages = [
            {"role": "system", "content": load_system(root, "ask", web_search=False)},
            {"role": "user", "content": goal},
        ]
        emit({"type": "step", "step": 1, "action": "ask", "thought": "Réponse directe", "args": {}})
        text = chat_text(messages)
        print(f"==> {text[:200]}")
        emit({"type": "done", "result": text})
        return text

    tools = _registry_for(mode, web_search)
    mem = Memory(system=load_system(root, mode, web_search=web_search))
    mem.add_user(goal)

    for step in range(1, max_steps + 1):
        decision = chat(mem.for_llm())
        action = decision.get("action", "")
        args = decision.get("args") or {}
        thought = decision.get("thought", "")
        print(f"[{step}] {action} — {thought}")
        emit(
            {
                "type": "step",
                "step": step,
                "action": action,
                "thought": thought,
                "args": args,
            }
        )

        if action == "finish":
            msg = args.get("message", "terminé")
            print(f"==> {msg}")
            emit({"type": "done", "result": msg})
            return msg

        if action not in tools:
            obs = (
                f"ERREUR: action inconnue '{action}'. "
                f"Valides: {list(tools)} + finish"
            )
        else:
            try:
                obs = tools[action](args)
            except Exception as e:
                obs = f"ERREUR: {e}"

        print(f"    {obs[:200]}")
        emit({"type": "observation", "step": step, "obs": obs[:2000]})
        mem.add_assistant(decision)
        mem.add_observation(obs)

    msg = "STOP: budget d'étapes épuisé"
    emit({"type": "done", "result": msg})
    return msg
