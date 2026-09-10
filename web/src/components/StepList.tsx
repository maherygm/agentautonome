/**
 * Timeline conversationnelle style Cursor : tours user + outils + réponse.
 */
import { useState } from "react";
import type { AgentEvent } from "../api";

/** Élément plat reçu de l'App (message user ou événement SSE). */
export type TimelineItem =
  | { kind: "user"; text: string }
  | { kind: "event"; event: AgentEvent };

type Props = {
  items: TimelineItem[];
  running?: boolean;
};

type ToolPair = {
  step: Extract<AgentEvent, { type: "step" }>;
  observation?: Extract<AgentEvent, { type: "observation" }>;
};

type AgentBlock =
  | { kind: "tool"; pair: ToolPair }
  | { kind: "done"; result: string }
  | { kind: "error"; message: string };

type Turn = {
  user: string;
  blocks: AgentBlock[];
};

/** Regroupe les items plats en tours (user puis blocs agent). */
function groupItems(items: TimelineItem[]): Turn[] {
  const turns: Turn[] = [];
  let current: Turn | null = null;

  for (const item of items) {
    if (item.kind === "user") {
      current = { user: item.text, blocks: [] };
      turns.push(current);
      continue;
    }
    if (!current) {
      current = { user: "", blocks: [] };
      turns.push(current);
    }

    const ev = item.event;
    if (ev.type === "step") {
      current.blocks.push({ kind: "tool", pair: { step: ev } });
    } else if (ev.type === "observation") {
      const last = current.blocks[current.blocks.length - 1];
      if (last?.kind === "tool" && !last.pair.observation) {
        last.pair.observation = ev;
      } else {
        current.blocks.push({
          kind: "tool",
          pair: {
            step: {
              type: "step",
              step: ev.step,
              action: "observation",
              thought: "",
            },
            observation: ev,
          },
        });
      }
    } else if (ev.type === "done") {
      current.blocks.push({ kind: "done", result: ev.result });
    } else {
      current.blocks.push({ kind: "error", message: ev.message });
    }
  }

  return turns;
}

function summarizeArgs(args?: Record<string, unknown>): string {
  if (!args || Object.keys(args).length === 0) return "";
  const parts = Object.entries(args).map(([k, v]) => {
    const val = typeof v === "string" ? v : JSON.stringify(v);
    const short = val.length > 80 ? `${val.slice(0, 77)}…` : val;
    return `${k}: ${short}`;
  });
  return parts.join(" · ");
}

function previewLine(text: string, max = 90): string {
  const flat = text.replace(/\s+/g, " ").trim();
  if (!flat) return "";
  return flat.length > max ? `${flat.slice(0, max - 1)}…` : flat;
}

function ThinkingBlock({
  thought,
  defaultOpen,
}: {
  thought: string;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(Boolean(defaultOpen));
  if (!thought.trim()) return null;

  return (
    <div className={`thinking ${open ? "open" : ""}`}>
      <button
        type="button"
        className="collapse-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="chevron" aria-hidden>
          ▸
        </span>
        Thinking
      </button>
      <div className="collapse-body">
        <p>{thought}</p>
      </div>
    </div>
  );
}

function ToolCall({
  pair,
  isActive,
}: {
  pair: ToolPair;
  isActive?: boolean;
}) {
  const { step, observation } = pair;
  const [open, setOpen] = useState(Boolean(isActive && !observation));
  const argsSummary = summarizeArgs(step.args);
  const hasOutput = Boolean(observation?.obs);
  const preview = observation ? previewLine(observation.obs) : "";

  return (
    <div className={`tool-call ${open ? "open" : ""} ${isActive ? "active" : ""}`}>
      <ThinkingBlock thought={step.thought} defaultOpen={isActive && !observation} />

      <button
        type="button"
        className="tool-row"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        disabled={!hasOutput && !argsSummary}
      >
        <span className="chevron" aria-hidden>
          ▸
        </span>
        <span className="tool-status" aria-hidden>
          {observation ? "✓" : isActive ? "◉" : "○"}
        </span>
        <span className="tool-name">{step.action}</span>
        {argsSummary && <span className="tool-args">{argsSummary}</span>}
        {!open && preview && <span className="tool-preview">{preview}</span>}
      </button>

      {(hasOutput || argsSummary) && (
        <div className="collapse-body tool-details">
          {argsSummary && (
            <div className="tool-args-full mono">{argsSummary}</div>
          )}
          {hasOutput && <pre className="mono tool-output">{observation!.obs}</pre>}
        </div>
      )}
    </div>
  );
}

function AssistantReply({ result }: { result: string }) {
  return (
    <article className="msg-assistant">
      <p>{result}</p>
    </article>
  );
}

/** Affiche la timeline groupée (thinking, outils, réponse finale). */
export function StepList({ items, running = false }: Props) {
  if (items.length === 0) return null;

  const turns = groupItems(items);
  const lastTurn = turns[turns.length - 1];
  const lastToolIndex =
    lastTurn?.blocks.reduce(
      (acc, b, i) => (b.kind === "tool" ? i : acc),
      -1,
    ) ?? -1;

  return (
    <div className="timeline">
      {turns.map((turn, ti) => {
        const isLastTurn = ti === turns.length - 1;
        return (
          <section key={ti} className="turn">
            {turn.user && (
              <article className="msg-user">
                <p>{turn.user}</p>
              </article>
            )}
            <div className="agent-blocks">
              {turn.blocks.map((block, bi) => {
                if (block.kind === "tool") {
                  const isActive =
                    running &&
                    isLastTurn &&
                    bi === lastToolIndex &&
                    !block.pair.observation;
                  return (
                    <ToolCall
                      key={bi}
                      pair={block.pair}
                      isActive={isActive}
                    />
                  );
                }
                if (block.kind === "done") {
                  return <AssistantReply key={bi} result={block.result} />;
                }
                return (
                  <article key={bi} className="msg-error">
                    <p>{block.message}</p>
                  </article>
                );
              })}
              {running && isLastTurn && turn.blocks.every((b) => b.kind !== "done") && (
                <div className="agent-pending" aria-live="polite">
                  <span className="pending-dot" />
                  Working…
                </div>
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
}
