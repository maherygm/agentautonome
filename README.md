# Agent autonome local (Ollama)

Boucle DIY légère : Python + Ollama local, avec CLI et interface React.

## Prérequis

1. [Ollama](https://ollama.com) installé et démarré (`ollama serve`)
2. Python 3.10+
3. Node.js 18+
4. Modèle :

```bash
ollama pull qwen2.5:7b
```

## Installation

```bash
pip install -r requirements.txt
cd web && npm install && cd ..
```

## CLI

```bash
python main.py "Liste les fichiers du projet puis finish"
python main.py "Crée hello.txt avec bonjour" --steps 8
python main.py "Lis README.md" --root . --model qwen2.5:7b
```

## Interface web

### Tout lancer d’un coup

```bash
# Git Bash / Linux / macOS
./start.sh
```

Sur Windows (double-clic ou cmd) :

```bat
start.bat
```

Cela démarre l’API (`:8000`) et l’UI (`:5173`). Ctrl+C (script bash) ou fermer les fenêtres (`.bat`).

### Manuellement (deux terminaux)

```bash
# API (SSE)
python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000

# UI
cd web && npm run dev
```

Ouvre http://localhost:5173 — l’UI proxy `/api` vers le serveur FastAPI.

### Modes

| Mode | Rôle |
|------|------|
| **Ask** | Question / réponse (texte direct, ou outils web si toggle Web actif) |
| **Plan** | Exploration lecture seule + plan d’action (`finish`) |
| **Agentic** | Exécution complète (fichiers, shell, web) |

### Toggle Web

Dans le composer, le bouton **Web** active ou désactive `web_search` et `fetch_url` pour le run.

## Variables d'environnement

Copier l'exemple puis adapter :

```bash
cp .env.example .env
```

| Variable | Défaut | Rôle |
|----------|--------|------|
| `OLLAMA_MODEL` | `qwen2.5:7b` | Modèle Ollama |
| `OLLAMA_URL` | `http://localhost:11434/api/chat` | Endpoint chat |

Côté UI (optionnel) : `cp web/.env.example web/.env` — le proxy Vite vers `:8000` suffit en local.
## Architecture

```
agentautonome/
  agent/           # boucle DIY + tools
  server/app.py    # FastAPI + SSE /api/run
  web/             # React TS (Vite)
  prompts/         # consignes système par mode
  main.py          # CLI
```

## Outils

- `list_dir`, `read_file`, `write_file` — sandbox sous `--root` / réglage Racine
- `run_shell` — commandes autorisées : `ls`, `dir`, `pwd`, `git`, `pytest`, `python`, `python3`
- `web_search` — recherche DuckDuckGo (package `ddgs`)
- `fetch_url` — récupération de page (HTML nettoyé), avec garde-fous SSRF
- `finish` — termine la boucle
