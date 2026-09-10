"""API FastAPI : santé Ollama et exécution agent en streaming SSE."""
from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from typing import Any, Iterator, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import llm as ollama_llm
from agent.llm import ensure_ollama
from agent.loop import run_agent

app = FastAPI(title="Agent autonome local")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


class RunRequest(BaseModel):
    """Corps de la requête POST /api/run."""

    goal: str = Field(..., min_length=1, description="Objectif utilisateur")
    root: str | None = Field(None, description="Racine sandbox du projet")
    model: str | None = Field(None, description="Modèle Ollama à utiliser")
    steps: int = Field(default=8, ge=1, le=32, description="Budget d'étapes")
    mode: Literal["ask", "plan", "agentic"] = Field(
        "agentic", description="Mode d'exécution"
    )
    web_search: bool = Field(
        True, description="Autoriser web_search et fetch_url"
    )


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Vérifie qu'Ollama est joignable et renvoie le modèle courant."""
    try:
        ensure_ollama()
    except SystemExit:
        raise HTTPException(
            status_code=503,
            detail="Ollama inaccessible. Lance `ollama serve`.",
        ) from None
    return {
        "ok": True,
        "model": ollama_llm.MODEL,
        "ollama_url": ollama_llm.OLLAMA_URL,
    }


@app.post("/api/run")
def run(req: RunRequest) -> StreamingResponse:
    """Lance l'agent en arrière-plan et streame les événements SSE."""
    root = Path(req.root).resolve() if req.root else _REPO_ROOT
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"root invalide: {root}")

    events: queue.Queue[dict[str, Any] | None] = queue.Queue()
    previous_model = ollama_llm.MODEL

    def on_event(event: dict[str, Any]) -> None:
        events.put(event)

    def worker() -> None:
        try:
            if req.model:
                ollama_llm.MODEL = req.model
            run_agent(
                req.goal,
                project_root=root,
                max_steps=req.steps,
                mode=req.mode,
                web_search=req.web_search,
                on_event=on_event,
            )
        except SystemExit:
            events.put(
                {
                    "type": "error",
                    "message": "Ollama inaccessible. Lance `ollama serve`.",
                }
            )
        except Exception as e:
            events.put({"type": "error", "message": str(e)})
        finally:
            ollama_llm.MODEL = previous_model
            events.put(None)

    def stream() -> Iterator[str]:
        threading.Thread(target=worker, daemon=True).start()
        while True:
            item = events.get()
            if item is None:
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
