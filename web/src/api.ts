/**
 * Client HTTP pour l'API agent : health check et streaming SSE des runs.
 */

/** Événements émis par `/api/run` (Server-Sent Events). */
export type AgentEvent =
  | {
      type: "step";
      step: number;
      action: string;
      thought: string;
      args?: Record<string, unknown>;
    }
  | { type: "observation"; step: number; obs: string }
  | { type: "done"; result: string }
  | { type: "error"; message: string };

/** Modes d'exécution alignés avec le backend. */
export type AgentMode = "ask" | "plan" | "agentic";

/** Options d'un run agent streamé. */
export type RunOptions = {
  goal: string;
  root?: string;
  model?: string;
  steps?: number;
  mode?: AgentMode;
  /** Active les outils `web_search` / `fetch_url`. */
  webSearch?: boolean;
  signal?: AbortSignal;
  onEvent: (event: AgentEvent) => void;
};

/** Réponse de `GET /api/health`. */
export type HealthResponse = {
  ok: boolean;
  model: string;
  ollama_url: string;
};

/** Vérifie que l'API et Ollama sont joignables. */
export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch("/api/health");
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Health ${res.status}`);
  }
  return res.json();
}

/**
 * Lance un run agent et appelle `onEvent` pour chaque événement SSE.
 * Se termine quand le flux se ferme (done / error / abort).
 */
export async function runAgentStream(opts: RunOptions): Promise<void> {
  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({
      goal: opts.goal,
      root: opts.root || undefined,
      model: opts.model || undefined,
      steps: opts.steps ?? 8,
      mode: opts.mode ?? "agentic",
      web_search: opts.webSearch ?? true,
    }),
    signal: opts.signal,
  });

  if (!res.ok || !res.body) {
    const detail = await res.text();
    throw new Error(detail || `Run failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const line = chunk
        .split("\n")
        .map((l) => l.trim())
        .find((l) => l.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      opts.onEvent(JSON.parse(payload) as AgentEvent);
    }
  }
}
