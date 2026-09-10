/**
 * Panneau de réglages (modèle, steps, racine) — ouvert via la toolbar.
 */

/** Paramètres runtime envoyés à `/api/run`. */
export type Settings = {
  model: string;
  steps: number;
  root: string;
};

type Props = {
  settings: Settings;
  onChange: (next: Settings) => void;
  disabled?: boolean;
};

/**
 * Formulaire de réglages uniquement.
 * Le bouton d'ouverture (gear / modèle) est dans ChatPanel.
 */
export function SettingsPanel({ settings, onChange, disabled }: Props) {
  return (
    <div className="settings">
      <label>
        Modèle
        <input
          value={settings.model}
          disabled={disabled}
          onChange={(e) => onChange({ ...settings, model: e.target.value })}
          placeholder="qwen2.5:7b"
        />
      </label>
      <label>
        Steps
        <input
          type="number"
          min={1}
          max={32}
          value={settings.steps}
          disabled={disabled}
          onChange={(e) =>
            onChange({ ...settings, steps: Number(e.target.value) || 8 })
          }
        />
      </label>
      <label className="settings-root">
        Racine
        <input
          value={settings.root}
          disabled={disabled}
          onChange={(e) => onChange({ ...settings, root: e.target.value })}
          placeholder="chemin du workspace"
        />
      </label>
    </div>
  );
}
