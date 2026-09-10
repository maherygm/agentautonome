/**
 * Sélecteur de mode Ask / Plan / Agentic.
 */

/** Modes agent exposés dans l'UI. */
export type AgentMode = "ask" | "plan" | "agentic";

const MODES: { id: AgentMode; label: string }[] = [
  { id: "ask", label: "Ask" },
  { id: "plan", label: "Plan" },
  { id: "agentic", label: "Agentic" },
];

type Props = {
  mode: AgentMode;
  onChange: (mode: AgentMode) => void;
  disabled?: boolean;
};

/** Onglets de mode dans la toolbar du composer. */
export function ModeSwitch({ mode, onChange, disabled }: Props) {
  return (
    <div className="mode-switch" role="tablist" aria-label="Mode">
      {MODES.map((m) => (
        <button
          key={m.id}
          type="button"
          role="tab"
          aria-selected={mode === m.id}
          className={`mode-chip ${mode === m.id ? "active" : ""}`}
          disabled={disabled}
          onClick={() => onChange(m.id)}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
