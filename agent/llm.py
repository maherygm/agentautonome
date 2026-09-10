"""Client Ollama : chat JSON (décisions agent) et chat texte libre."""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.parse import urlparse

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def _base_url() -> str:
    """Retourne l'origine HTTP d'Ollama (sans le chemin /api/chat)."""
    parsed = urlparse(OLLAMA_URL)
    return f"{parsed.scheme}://{parsed.netloc}"


def ensure_ollama() -> None:
    """Vérifie qu'Ollama répond ; message clair sinon."""
    try:
        r = requests.get(f"{_base_url()}/api/tags", timeout=5)
        r.raise_for_status()
    except requests.RequestException as e:
        print(
            "Ollama inaccessible sur "
            f"{_base_url()}. Lance `ollama serve` puis réessaie.\n"
            f"Détail: {e}",
            file=sys.stderr,
        )
        raise SystemExit(1) from e


def _extract_json_object(text: str) -> str | None:
    """Extrait le premier objet JSON {...}, y compris depuis un fence markdown."""
    s = text.strip()
    if not s:
        return None

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.IGNORECASE)
    if fence:
        s = fence.group(1).strip()

    start = s.find("{")
    if start < 0:
        return None

    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def _parse_decision(raw: str | dict) -> dict | None:
    """Interprète la réponse modèle en décision ``{thought, action, args}``."""
    if isinstance(raw, dict):
        if "action" in raw:
            return raw
        # Ollama parfois renvoie déjà un dict parsé via format=json
        return raw if "thought" in raw else None

    text = str(raw).strip()
    if not text:
        return None

    candidates = [text]
    extracted = _extract_json_object(text)
    if extracted and extracted not in candidates:
        candidates.append(extracted)

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "action" in data:
            data.setdefault("thought", "")
            data.setdefault("args", {})
            if not isinstance(data["args"], dict):
                data["args"] = {"value": data["args"]}
            return data
    return None


def chat(
    messages: list[dict],
    *,
    temperature: float = 0.2,
    num_predict: int = 4096,
) -> dict:
    """Demande une décision agent JSON à Ollama.

    Returns:
        Dict ``thought`` / ``action`` / ``args``, ou ``finish`` en cas d'échec de parse.
    """
    raw = _post_chat(
        messages, temperature=temperature, num_predict=num_predict, as_json=True
    )
    parsed = _parse_decision(raw)
    if parsed is not None:
        return parsed

    preview = str(raw)[:400]
    truncated = len(str(raw)) >= 3500 or (
        isinstance(raw, str) and raw.rstrip().endswith((",", ":", '"', "{", "["))
    )
    hint = (
        " (réponse probablement tronquée — réessaie avec un write_file plus court "
        "ou plusieurs étapes)"
        if truncated
        else ""
    )
    return {
        "thought": "réponse non-JSON du modèle",
        "action": "finish",
        "args": {
            "message": f"ERREUR: réponse non-JSON du modèle{hint}: {preview}"
        },
    }


def chat_text(
    messages: list[dict],
    *,
    temperature: float = 0.4,
    num_predict: int = 2048,
) -> str:
    """Réponse texte libre (mode Ask sans outils)."""
    raw = _post_chat(
        messages, temperature=temperature, num_predict=num_predict, as_json=False
    )
    if isinstance(raw, dict):
        return str((raw.get("args") or {}).get("message") or raw)
    return str(raw)


def _post_chat(
    messages: list[dict],
    *,
    temperature: float,
    num_predict: int,
    as_json: bool,
) -> dict | str:
    """POST /api/chat Ollama ; renvoie le contenu message (str ou dict)."""
    payload: dict = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }
    if as_json:
        payload["format"] = "json"

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=300)
    except requests.RequestException as e:
        return {
            "thought": f"Ollama injoignable: {e}",
            "action": "finish",
            "args": {"message": f"ERREUR: Ollama injoignable ({e})"},
        }

    if r.status_code == 404:
        return {
            "thought": f"modèle manquant: {MODEL}",
            "action": "finish",
            "args": {
                "message": (
                    f"ERREUR: modèle '{MODEL}' introuvable. "
                    f"Lance: ollama pull {MODEL}"
                )
            },
        }

    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        return {
            "thought": f"erreur HTTP Ollama: {e}",
            "action": "finish",
            "args": {"message": f"ERREUR Ollama: {e} — {r.text[:300]}"},
        }

    content = r.json().get("message", {}).get("content", "")
    # format=json peut déjà arriver comme dict selon versions / clients
    if isinstance(content, dict):
        return content
    if isinstance(content, str) and content.strip().startswith("{"):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content
    return content
