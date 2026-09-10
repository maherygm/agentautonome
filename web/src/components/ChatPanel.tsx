/**
 * Composer de chat : textarea, modes, toggle Web, modèle et réglages.
 */
import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { ModeSwitch, type AgentMode } from "./ModeSwitch";
import { SettingsPanel, type Settings } from "./SettingsBar";

const TEXTAREA_MAX_PX = 140;

type Props = {
  mode: AgentMode;
  onModeChange: (mode: AgentMode) => void;
  /** Recherche / scraping web activés côté agent. */
  webSearch: boolean;
  onWebSearchChange: (enabled: boolean) => void;
  settings: Settings;
  onSettingsChange: (next: Settings) => void;
  health: string;
  settingsOpen: boolean;
  onSettingsToggle: () => void;
  running: boolean;
  onSubmit: (goal: string) => void;
  onStop: () => void;
};

/** True si le health check indique Ollama OK. */
function healthOk(health: string): boolean {
  return health.startsWith("OK");
}

/** Barre de saisie + toolbar (mode, Web, modèle, envoi). */
export function ChatPanel({
  mode,
  onModeChange,
  webSearch,
  onWebSearchChange,
  settings,
  onSettingsChange,
  health,
  settingsOpen,
  onSettingsToggle,
  running,
  onSubmit,
  onStop,
}: Props) {
  const [goal, setGoal] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  function resizeTextarea() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, TEXTAREA_MAX_PX)}px`;
  }

  useEffect(() => {
    resizeTextarea();
  }, [goal]);

  function handleSubmit(e?: FormEvent) {
    e?.preventDefault();
    const trimmed = goal.trim();
    if (!trimmed || running) return;
    onSubmit(trimmed);
    setGoal("");
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    });
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  const placeholder =
    mode === "ask"
      ? webSearch
        ? "Pose une question (recherche web activée)…"
        : "Pose une question…"
      : mode === "plan"
        ? "Décris ce que tu veux planifier…"
        : "Décris ta tâche pour l’agent…";

  const modelLabel = settings.model || "qwen2.5:7b";
  const ok = healthOk(health);

  return (
    <div className="composer-shell">
      {settingsOpen && (
        <div className="settings-popover" role="dialog" aria-label="Réglages">
          <SettingsPanel
            settings={settings}
            onChange={onSettingsChange}
            disabled={running}
          />
        </div>
      )}

      <form className="composer-pill" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          rows={1}
          disabled={running}
        />
        <div className="composer-toolbar">
          <ModeSwitch mode={mode} onChange={onModeChange} disabled={running} />
          <button
            type="button"
            className={`web-chip ${webSearch ? "active" : ""}`}
            disabled={running}
            aria-pressed={webSearch}
            title={
              webSearch
                ? "Recherche web activée (cliquer pour désactiver)"
                : "Activer la recherche web"
            }
            onClick={() => onWebSearchChange(!webSearch)}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M2 12h20" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
            Web
          </button>
          <div className="composer-spacer" />
          <button
            type="button"
            className="model-chip"
            title="Changer le modèle"
            onClick={onSettingsToggle}
            aria-expanded={settingsOpen}
          >
            {modelLabel}
          </button>
          <button
            type="button"
            className={`gear-btn ${ok ? "ok" : "bad"}`}
            onClick={onSettingsToggle}
            aria-label={`Réglages · ${health}`}
            aria-expanded={settingsOpen}
            title={health}
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
            <span className="gear-dot" aria-hidden />
          </button>
          {running ? (
            <button
              type="button"
              className="send-btn stop"
              onClick={onStop}
              aria-label="Stop"
            >
              ■
            </button>
          ) : (
            <button
              type="submit"
              className="send-btn"
              disabled={!goal.trim()}
              aria-label="Envoyer"
            >
              ↗
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
