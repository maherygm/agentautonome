/**
 * Application principale : état conversation, modes, layout idle / chat.
 */
import { useEffect, useRef, useState } from "react";
import { fetchHealth, runAgentStream } from "./api";
import { ChatPanel } from "./components/ChatPanel";
import { type AgentMode } from "./components/ModeSwitch";
import { type Settings } from "./components/SettingsBar";
import { StepList, type TimelineItem } from "./components/StepList";

const DEFAULT_SETTINGS: Settings = {
  model: "qwen2.5:7b",
  steps: 8,
  root: "",
};

/** Racine UI : composer, timeline et orchestration des runs agent. */
export default function App() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [mode, setMode] = useState<AgentMode>("agentic");
  const [webSearch, setWebSearch] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [health, setHealth] = useState("…");
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const hasConversation = items.length > 0;

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((h) => {
        if (!cancelled) {
          setHealth(`OK · ${h.model}`);
          setSettings((s) => (s.model ? s : { ...s, model: h.model }));
        }
      })
      .catch(() => {
        if (!cancelled) setHealth("API hors ligne");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [items]);

  async function handleSubmit(goal: string) {
    setItems((prev) => [...prev, { kind: "user", text: goal }]);
    setRunning(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      await runAgentStream({
        goal,
        model: settings.model || undefined,
        steps: settings.steps,
        root: settings.root || undefined,
        mode,
        webSearch,
        signal: ctrl.signal,
        onEvent: (event) => {
          setItems((prev) => [...prev, { kind: "event", event }]);
        },
      });
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        setItems((prev) => [
          ...prev,
          { kind: "event", event: { type: "error", message: "Run interrompu" } },
        ]);
      } else {
        setItems((prev) => [
          ...prev,
          {
            kind: "event",
            event: {
              type: "error",
              message: err instanceof Error ? err.message : String(err),
            },
          },
        ]);
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }

  function handleStop() {
    abortRef.current?.abort();
  }

  const composer = (
    <ChatPanel
      mode={mode}
      onModeChange={setMode}
      webSearch={webSearch}
      onWebSearchChange={setWebSearch}
      settings={settings}
      onSettingsChange={setSettings}
      health={health}
      settingsOpen={settingsOpen}
      onSettingsToggle={() => setSettingsOpen((v) => !v)}
      running={running}
      onSubmit={handleSubmit}
      onStop={handleStop}
    />
  );

  return (
    <div className={`app ${hasConversation ? "has-chat" : "idle"}`}>
      <div className="glow" aria-hidden />

      <header className="hero">
        <p className="brand">AgentAutonome</p>
        {!hasConversation && (
          <>
            <h1>
              Opérations locales, <em>pilotées par l’IA</em>
            </h1>
            <p className="tagline">
              Ask pour questionner, Plan pour préparer, Agentic pour exécuter —
              via Ollama sur ta machine.
            </p>
          </>
        )}
      </header>

      {hasConversation ? (
        <>
          <main className="main">
            <StepList items={items} running={running} />
            <div ref={bottomRef} />
          </main>
          <div className="composer-dock">{composer}</div>
        </>
      ) : (
        <div className="composer-dock idle-dock">{composer}</div>
      )}
    </div>
  );
}
