/**
 * LogViewer component – real-time log pane with level-based syntax highlighting.
 *
 * Displays a scrollable, auto-scrolling list of ItemLog entries streamed from
 * the backend WebSocket processor. Each entry is colour-coded by severity:
 *   - INFO    → slate / neutral
 *   - SUCESSO → emerald / green
 *   - ERRO    → red
 *
 * Features:
 *   - Auto-scrolls to the latest entry (can be paused by the user scrolling up).
 *   - "Scroll to bottom" FAB appears when the user has scrolled away.
 *   - One-click "Limpar logs" button to reset the log list.
 *   - Maximum log retention (MAX_LOG_ENTRIES) to avoid memory pressure.
 *   - Accessible ARIA live region so screen readers announce new entries.
 *   - Premium dark-mode monospace styling with entry micro-animations.
 *
 * Props:
 *   logs     – ordered array of ItemLog objects to display.
 *   onClear  – callback fired when the user clicks "Limpar logs".
 *   maxLines – optional override for max visible lines before scrolling.
 *
 * Usage:
 *   <LogViewer logs={logItems} onClear={() => setLogItems([])} />
 */

import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { ChevronDown, Terminal, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ItemLog, TipoLog } from "@/services/api";

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const MAX_LOG_ENTRIES = 500;

// ─────────────────────────────────────────────────────────────────────────────
// Styling maps
// ─────────────────────────────────────────────────────────────────────────────

const LOG_LEVEL_STYLES: Record<TipoLog, { badge: string; text: string; row: string }> = {
  INFO: {
    badge: "bg-slate-700 text-slate-300",
    text: "text-slate-300",
    row: "hover:bg-slate-800/50",
  },
  SUCESSO: {
    badge: "bg-emerald-900/70 text-emerald-300",
    text: "text-emerald-200",
    row: "hover:bg-emerald-950/40",
  },
  ERRO: {
    badge: "bg-red-900/70 text-red-300",
    text: "text-red-200",
    row: "hover:bg-red-950/40",
  },
};

const LOG_LEVEL_LABELS: Record<TipoLog, string> = {
  INFO: "INFO",
  SUCESSO: "OK",
  ERRO: "ERR",
};

// ─────────────────────────────────────────────────────────────────────────────
// LogRow sub-component
// ─────────────────────────────────────────────────────────────────────────────

interface LogRowProps {
  entry: ItemLog;
  index: number;
}

const LogRow = React.memo(function LogRow({ entry, index }: LogRowProps) {
  const styles = LOG_LEVEL_STYLES[entry.tipo];
  return (
    <li
      className={cn(
        "flex items-start gap-2.5 rounded-md px-3 py-1.5 text-xs font-mono transition-colors duration-150 animate-fade-in",
        styles.row
      )}
      aria-label={`[${entry.tipo}] ${entry.timestamp} – ${entry.mensagem}`}
    >
      {/* Timestamp */}
      <span className="mt-0.5 shrink-0 font-mono text-[10px] text-slate-500">
        {entry.timestamp}
      </span>

      {/* Level badge */}
      <span
        className={cn(
          "mt-0.5 inline-flex shrink-0 items-center rounded px-1.5 py-px text-[10px] font-bold uppercase tracking-wider",
          styles.badge
        )}
      >
        {LOG_LEVEL_LABELS[entry.tipo]}
      </span>

      {/* Message */}
      <span className={cn("flex-1 break-words leading-relaxed", styles.text)}>
        {entry.mensagem}
      </span>
    </li>
  );
});

// ─────────────────────────────────────────────────────────────────────────────
// LogViewer component
// ─────────────────────────────────────────────────────────────────────────────

export interface LogViewerProps {
  /** Ordered list of log entries to display. */
  logs: ItemLog[];
  /** Called when the user clicks the clear button. */
  onClear?: () => void;
  /** Maximum height of the scrollable area (CSS value). Defaults to '400px'. */
  maxHeight?: string;
}

export function LogViewer({
  logs,
  onClear,
  maxHeight = "400px",
}: LogViewerProps) {
  const containerRef = useRef<HTMLUListElement>(null);
  const [userScrolled, setUserScrolled] = useState(false);

  // Clamp logs to MAX_LOG_ENTRIES (newest kept)
  const visibleLogs =
    logs.length > MAX_LOG_ENTRIES
      ? logs.slice(logs.length - MAX_LOG_ENTRIES)
      : logs;

  // ── Auto-scroll to bottom unless the user has scrolled up ─────────────────
  useLayoutEffect(() => {
    if (userScrolled) return;
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [visibleLogs, userScrolled]);

  // ── Track whether the user has manually scrolled away from the bottom ──────
  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const isAtBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setUserScrolled(!isAtBottom);
  }, []);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
      setUserScrolled(false);
    }
  }, []);

  return (
    <section
      id="log-viewer-section"
      aria-label="Painel de logs em tempo real"
      className="flex flex-col gap-0 overflow-hidden rounded-2xl border border-slate-800 bg-slate-950"
    >
      {/* Header */}
      <header className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <Terminal className="h-4 w-4 text-indigo-400" aria-hidden />
          <span>Logs de Execução</span>
          {logs.length > 0 && (
            <span className="rounded-full bg-slate-800 px-2 py-px text-[10px] font-medium text-slate-400">
              {logs.length}
            </span>
          )}
        </div>
        {onClear && logs.length > 0 && (
          <button
            id="clear-logs-button"
            type="button"
            aria-label="Limpar todos os logs"
            onClick={onClear}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden />
            Limpar
          </button>
        )}
      </header>

      {/* Log list */}
      <div className="relative">
        <ul
          ref={containerRef}
          id="log-entries-list"
          role="log"
          aria-live="polite"
          aria-label="Entradas de log do processamento"
          className="overflow-y-auto px-2 py-2"
          style={{ maxHeight }}
          onScroll={handleScroll}
        >
          {visibleLogs.length === 0 ? (
            <li className="flex flex-col items-center gap-2 py-12 text-center text-slate-600">
              <Terminal className="h-8 w-8 opacity-40" aria-hidden />
              <p className="text-xs">
                Os logs aparecerão aqui durante o processamento.
              </p>
            </li>
          ) : (
            visibleLogs.map((entry, i) => (
              <LogRow key={`${entry.timestamp}-${i}`} entry={entry} index={i} />
            ))
          )}
        </ul>

        {/* Scroll-to-bottom FAB */}
        {userScrolled && logs.length > 0 && (
          <button
            id="scroll-to-bottom-button"
            type="button"
            aria-label="Ir para o final dos logs"
            onClick={scrollToBottom}
            className={cn(
              "absolute bottom-3 right-3 flex items-center gap-1.5 rounded-full",
              "bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white shadow-lg",
              "transition-all duration-200 hover:bg-indigo-500 animate-fade-in"
            )}
          >
            <ChevronDown className="h-3.5 w-3.5" aria-hidden />
            Fim
          </button>
        )}
      </div>
    </section>
  );
}

export default LogViewer;
