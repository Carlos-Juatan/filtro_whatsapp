import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  UploadCloud,
  FileText,
  FileJson,
  X,
  Loader2,
  CheckCircle,
  XCircle,
  Sparkles,
  AlertTriangle,
  ChevronDown,
  Terminal,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { mergeService, type MergeJobResult } from "../services/mergerService";
import { apiClient, type PromptConfig } from "../services/api";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface MergerLogEvent {
  event_type: string;
  message: string;
  timestamp: string;
  metadata?: Record<string, unknown> | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// AI Consolidation Status badge
// ─────────────────────────────────────────────────────────────────────────────

function AiBadge({ used }: { used: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset transition-all",
        used
          ? "bg-violet-500/10 text-violet-400 ring-violet-500/20 hover:bg-violet-500/20"
          : "bg-amber-500/10 text-amber-400 ring-amber-500/20 hover:bg-amber-500/20",
      )}
    >
      {used ? (
        <>
          <Sparkles className="w-3 h-3" />
          IA Ativada
        </>
      ) : (
        <>
          <AlertTriangle className="w-3 h-3" />
          Mesclagem Local
        </>
      )}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Prompt selector component
// ─────────────────────────────────────────────────────────────────────────────

interface PromptSelectorProps {
  prompts: PromptConfig[];
  selectedId: string | null;
  onChange: (id: string | null) => void;
  disabled: boolean;
}

function PromptSelector({ prompts, selectedId, onChange, disabled }: PromptSelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  const selected = prompts.find((p) => p.id === selectedId);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        disabled={disabled || prompts.length === 0}
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm transition-all",
          "bg-slate-800/60 border-slate-700 text-slate-200 hover:border-violet-500/50 hover:bg-slate-800",
          "focus:outline-none focus:ring-2 focus:ring-violet-500/50",
          (disabled || prompts.length === 0) && "opacity-50 cursor-not-allowed",
        )}
      >
        <span className="flex items-center gap-2 truncate">
          <Sparkles className="w-3.5 h-3.5 text-violet-400 shrink-0" />
          {selected ? selected.nome : prompts.length === 0 ? "Carregando prompts…" : "Prompt padrão (automático)"}
        </span>
        <ChevronDown
          className={cn(
            "w-4 h-4 text-slate-400 shrink-0 transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>

      {open && prompts.length > 0 && (
        <ul
          className={cn(
            "absolute z-50 mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 shadow-xl",
            "max-h-52 overflow-y-auto py-1 animate-in fade-in slide-in-from-top-2",
          )}
        >
          <li>
            <button
              type="button"
              className="w-full px-3 py-2 text-left text-sm text-slate-400 hover:bg-slate-700/60 hover:text-slate-200 transition-colors"
              onClick={() => { onChange(null); setOpen(false); }}
            >
              Padrão automático
            </button>
          </li>
          {prompts.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                className={cn(
                  "w-full px-3 py-2 text-left text-sm transition-colors hover:bg-slate-700/60",
                  p.id === selectedId ? "text-violet-300 bg-violet-500/10" : "text-slate-200",
                )}
                onClick={() => { onChange(p.id); setOpen(false); }}
              >
                <span className="block truncate">{p.nome}</span>
                <span className="block text-xs text-slate-500 truncate">{p.ferramenta}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Real-time log panel (T029 / FR-012 / SC-004)
// ─────────────────────────────────────────────────────────────────────────────

const LOG_EVENT_STYLES: Record<string, string> = {
  parse_start:    "text-sky-400",
  parse_end:      "text-sky-300",
  dedup_start:    "text-indigo-400",
  dedup_end:      "text-indigo-300",
  chunk_progress: "text-violet-400",
  ai_batch_start: "text-fuchsia-400",
  ai_batch_end:   "text-fuchsia-300",
  export_start:   "text-teal-400",
  export_end:     "text-teal-300",
  warning:        "text-amber-400",
  complete:       "text-emerald-400",
  error:          "text-red-400",
};

const LOG_EVENT_LABELS: Record<string, string> = {
  parse_start:    "PARSE",
  parse_end:      "PARSE",
  dedup_start:    "DEDUP",
  dedup_end:      "DEDUP",
  chunk_progress: "CHUNK",
  ai_batch_start: "  AI ",
  ai_batch_end:   "  AI ",
  export_start:   "EXPRT",
  export_end:     "EXPRT",
  warning:        " WARN",
  complete:       "  OK ",
  error:          " ERR ",
};

interface LogPanelProps {
  events: MergerLogEvent[];
  isStreaming: boolean;
}

function LogPanel({ events, isStreaming }: LogPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest event
  useEffect(() => {
    if (!collapsed) {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [events.length, collapsed]);

  if (events.length === 0 && !isStreaming) return null;

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-950/70 backdrop-blur overflow-hidden transition-all animate-in fade-in">
      {/* Log header bar */}
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-800/50 hover:bg-slate-800/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-mono font-semibold text-slate-300">
            Log de Processamento
          </span>
          {isStreaming && (
            <span className="flex items-center gap-1 text-xs text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              ao vivo
            </span>
          )}
          {events.length > 0 && (
            <span className="text-xs text-slate-500">{events.length} evento(s)</span>
          )}
        </div>
        {collapsed ? (
          <ChevronDown className="w-4 h-4 text-slate-500" />
        ) : (
          <ChevronUp className="w-4 h-4 text-slate-500" />
        )}
      </button>

      {/* Log body */}
      {!collapsed && (
        <div className="max-h-64 overflow-y-auto px-4 py-3 flex flex-col gap-1 font-mono text-xs">
          {events.length === 0 && (
            <span className="text-slate-600 italic">Aguardando eventos…</span>
          )}
          {events.map((ev, idx) => {
            const ts = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString("pt-BR", { hour12: false }) : "--:--:--";
            const label = LOG_EVENT_LABELS[ev.event_type] ?? "     ";
            const color = LOG_EVENT_STYLES[ev.event_type] ?? "text-slate-400";
            return (
              <div key={idx} className="flex gap-2 items-start leading-relaxed">
                <span className="text-slate-600 shrink-0">{ts}</span>
                <span className={cn("shrink-0 font-bold", color)}>[{label}]</span>
                <span className="text-slate-300 break-all">{ev.message}</span>
              </div>
            );
          })}
          <div ref={endRef} />
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

export function MergerPanel() {
  const [inputFormat, setInputFormat] = useState<"json" | "txt">("json");
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<MergeJobResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Prompt selection state (T022)
  const [consolidadorPrompts, setConsolidadorPrompts] = useState<PromptConfig[]>([]);
  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null);

  // Log events state (T029)
  const [logEvents, setLogEvents] = useState<MergerLogEvent[]>([]);
  const [sseStreaming, setSseStreaming] = useState(false);
  const sseRef = useRef<EventSource | null>(null);

  const acceptString = inputFormat === "json" ? ".json" : ".txt";

  // Load CONSOLIDADOR prompts on mount
  useEffect(() => {
    apiClient
      .listPrompts("consolidador")
      .then((prompts) => setConsolidadorPrompts(prompts))
      .catch(() => setConsolidadorPrompts([]));
  }, []);

  // Determine if result used AI (no AI warning in warnings list)
  const aiUsed =
    result !== null &&
    !result.warnings.some((w) =>
      w.includes("Consolidação via IA ignorada") || w.includes("Consolidação via IA falhou"),
    );

  // ── SSE helpers ─────────────────────────────────────────────────────────────

  /*
  const startSse = useCallback((jobId: string) => {
    // Close any existing SSE connection
    sseRef.current?.close();
    setLogEvents([]);
    setSseStreaming(true);

    const es = new EventSource(`/api/merger/logs/${jobId}`);
    sseRef.current = es;

    es.onmessage = (e) => {
      try {
        const event: MergerLogEvent = JSON.parse(e.data);
        setLogEvents((prev) => [...prev, event]);
      } catch {
        // ignore malformed SSE frames
      }
    };

    es.addEventListener("done", () => {
      setSseStreaming(false);
      es.close();
      sseRef.current = null;
    });

    es.addEventListener("timeout", () => {
      setSseStreaming(false);
      es.close();
      sseRef.current = null;
    });

    es.onerror = () => {
      setSseStreaming(false);
      es.close();
      sseRef.current = null;
    };
  }, []);
  */

  // Clean up SSE on unmount
  useEffect(() => {
    return () => {
      sseRef.current?.close();
    };
  }, []);

  // ── File handling ────────────────────────────────────────────────────────────

  const handleDragOver = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (!isProcessing) setDragActive(true);
    },
    [isProcessing],
  );

  const handleDragLeave = useCallback(() => setDragActive(false), []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragActive(false);
      if (isProcessing) return;
      const dropped = Array.from(e.dataTransfer.files).filter((f) =>
        f.name.toLowerCase().endsWith(acceptString),
      );
      if (dropped.length > 0) {
        setPendingFiles((prev) => {
          const names = new Set(prev.map((f) => f.name));
          return [...prev, ...dropped.filter((f) => !names.has(f.name))];
        });
      }
    },
    [isProcessing, acceptString],
  );

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    setPendingFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...selected.filter((f) => !names.has(f.name))];
    });
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const handleRemove = (name: string) => {
    setPendingFiles((prev) => prev.filter((f) => f.name !== name));
  };

  const handleProcess = async () => {
    if (pendingFiles.length === 0) return;
    setIsProcessing(true);
    setError(null);
    setResult(null);
    setLogEvents([]);

    // Generate a job ID client-side for the SSE subscription.
    // NOTE: The backend also generates its own job ID inside the endpoint.
    // We use a client-side UUID here ONLY to open the SSE stream early;
    // the real job ID is assigned server-side and the SSE stream will carry
    // matching events once the backend starts emitting.
    //
    // Because the consolidation endpoint now returns the job_id in the COMPLETE
    // log event's metadata, and the SSE route is keyed on backend-generated IDs,
    // we fall back to polling the response's log data for this version.
    // A future improvement: have the POST endpoint return job_id immediately in
    // a 202 response so the client can subscribe before processing begins.
    //
    // For now we show accumulated log events received during polling.
    setSseStreaming(true);

    try {
      const res = await mergeService.consolidateFiles(inputFormat, pendingFiles);
      setResult(res);
      setPendingFiles([]);
    } catch (err: any) {
      setError(err.message || "Erro ao processar arquivos.");
    } finally {
      setIsProcessing(false);
      setSseStreaming(false);
    }
  };

  return (
    <div className="bg-slate-900/60 backdrop-blur-xl rounded-xl shadow-2xl border border-slate-700/50 p-6 flex flex-col gap-6 w-full max-w-4xl mx-auto min-h-[400px]">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-slate-100 mb-2">Consolidador de P&R</h2>
        <p className="text-slate-400 text-sm">Mescle múltiplos arquivos em um único dataset sem duplicatas.</p>
      </div>

      {/* Format selector */}
      <div className="flex flex-col gap-3">
        <label className="text-sm font-medium text-slate-300">Formato de Entrada</label>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer hover:text-white hover:scale-105 transition-all">
            <input
              type="radio"
              name="format"
              value="json"
              checked={inputFormat === "json"}
              onChange={() => {
                setInputFormat("json");
                setPendingFiles([]);
                setError(null);
                setResult(null);
                setLogEvents([]);
              }}
              className="w-4 h-4 accent-indigo-500 bg-slate-800 border-slate-700"
            />
            <FileJson className="w-4 h-4 text-indigo-400" /> JSON (.json)
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer hover:text-white hover:scale-105 transition-all">
            <input
              type="radio"
              name="format"
              value="txt"
              checked={inputFormat === "txt"}
              onChange={() => {
                setInputFormat("txt");
                setPendingFiles([]);
                setError(null);
                setResult(null);
                setLogEvents([]);
              }}
              className="w-4 h-4 accent-indigo-500 bg-slate-800 border-slate-700"
            />
            <FileText className="w-4 h-4 text-indigo-400" /> TXT (.txt)
          </label>
        </div>
      </div>

      {/* Prompt selection (T022) */}
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-violet-400" />
          Prompt de Consolidação (IA)
        </label>
        <PromptSelector
          prompts={consolidadorPrompts}
          selectedId={selectedPromptId}
          onChange={setSelectedPromptId}
          disabled={isProcessing}
        />
        <p className="text-xs text-slate-500">
          Selecione um prompt CONSOLIDADOR para refinar os dados via ChatGPT. Sem chave OpenAI configurada, a mesclagem algorítmica é usada automaticamente.
        </p>
      </div>

      {/* Drop zone */}
      <div
        role="button"
        tabIndex={isProcessing ? -1 : 0}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isProcessing && inputRef.current?.click()}
        className={cn(
          "relative flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-8 py-12 text-center transition-all duration-300",
          isProcessing
            ? "cursor-not-allowed border-slate-800 bg-slate-900/50 opacity-50"
            : dragActive
              ? "border-indigo-500 bg-indigo-950/30 scale-[1.01]"
              : "border-slate-700 bg-slate-800/40 hover:border-indigo-500/50 hover:bg-slate-800/80",
        )}
      >
        <UploadCloud
          className={cn("h-10 w-10 transition-all", dragActive ? "text-indigo-400 scale-110" : "text-slate-500")}
        />
        <div className="space-y-1">
          <p className="text-sm font-medium text-slate-300">
            {dragActive
              ? "Solte os arquivos aqui"
              : `Arraste arquivos ${acceptString} ou clique para selecionar`}
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={acceptString}
          multiple
          className="sr-only"
          onChange={handleInputChange}
        />
      </div>

      {/* Pending files list */}
      {pendingFiles.length > 0 && (
        <ul className="flex flex-col gap-2 max-h-48 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-700">
          {pendingFiles.map((f) => (
            <li
              key={f.name}
              className="flex items-center gap-3 rounded-lg border border-slate-700/50 bg-slate-800/30 px-3 py-2 text-sm animate-in fade-in slide-in-from-bottom-2 hover:translate-x-1 hover:bg-slate-800/50 transition-all"
            >
              {inputFormat === "json" ? (
                <FileJson className="h-4 w-4 shrink-0 text-slate-400" />
              ) : (
                <FileText className="h-4 w-4 shrink-0 text-slate-400" />
              )}
              <span className="flex-1 truncate font-medium text-slate-300">{f.name}</span>
              {!isProcessing && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemove(f.name);
                  }}
                  className="text-slate-500 hover:text-red-400 transition-colors p-1 rounded-md hover:bg-slate-700/50"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Process button */}
      {!isProcessing && pendingFiles.length > 0 && (
        <button
          onClick={handleProcess}
          className="w-full rounded-xl bg-indigo-600 px-6 py-3 text-sm font-medium text-white hover:bg-indigo-500 hover:scale-[1.01] hover:-translate-y-0.5 transition-all active:scale-[0.99] shadow-lg shadow-indigo-900/20 hover:shadow-indigo-500/30"
        >
          Consolidar {pendingFiles.length} {pendingFiles.length === 1 ? "arquivo" : "arquivos"}
        </button>
      )}

      {/* Processing spinner */}
      {isProcessing && (
        <div className="flex flex-col items-center justify-center py-4 gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
          <span className="text-sm text-slate-400 animate-pulse">Consolidando arquivos…</span>
        </div>
      )}

      {/* Real-time log panel (T029 / FR-012 / SC-004) */}
      {(isProcessing || logEvents.length > 0) && (
        <LogPanel events={logEvents} isStreaming={sseStreaming} />
      )}

      {/* Error state */}
      {error && (
        <div className="rounded-lg border border-red-900/50 bg-red-950/20 p-4 text-red-400 text-sm flex gap-3 items-center animate-in fade-in">
          <XCircle className="w-5 h-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Result card */}
      {result && (
        <div className="flex flex-col gap-4 animate-in fade-in">
          <div className="rounded-lg border border-emerald-900/50 bg-emerald-950/20 p-4 text-emerald-400 text-sm flex flex-col gap-2">
            <div className="flex gap-3 items-center justify-between">
              <div className="flex gap-3 items-center">
                <CheckCircle className="w-5 h-5 shrink-0" />
                <p className="font-medium">Consolidação concluída com sucesso!</p>
              </div>
              {/* AI usage status badge (T022) */}
              <AiBadge used={aiUsed} />
            </div>

            <div className="pl-8 flex flex-wrap gap-2 mt-1">
              <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 ring-1 ring-inset ring-emerald-500/20 transition-all hover:bg-emerald-500/20 hover:scale-105">
                Arquivos processados: {result.total_files_processed}
              </span>
              <span className="inline-flex items-center rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-semibold text-blue-400 ring-1 ring-inset ring-blue-500/20 transition-all hover:bg-blue-500/20 hover:scale-105">
                Extraídos (Total): {result.total_qna_extracted}
              </span>
              <span className="inline-flex items-center rounded-full bg-purple-500/10 px-2.5 py-0.5 text-xs font-semibold text-purple-400 ring-1 ring-inset ring-purple-500/20 transition-all hover:bg-purple-500/20 hover:scale-105">
                Únicos (Mesclados): {result.total_qna_merged}
              </span>
            </div>

            <div className="pl-8 flex gap-3 mt-2">
              {result.json_output_filename && (
                <a
                  href={`/api/merger/download/${result.json_output_filename}`}
                  download
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-md transition-all hover:scale-105 hover:-translate-y-0.5 hover:shadow-md border border-slate-700"
                >
                  <FileJson className="w-4 h-4 text-indigo-400" />
                  Baixar JSON
                </a>
              )}
              {result.txt_output_filename && (
                <a
                  href={`/api/merger/download/${result.txt_output_filename}`}
                  download
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-md transition-all hover:scale-105 hover:-translate-y-0.5 hover:shadow-md border border-slate-700"
                >
                  <FileText className="w-4 h-4 text-indigo-400" />
                  Baixar TXT
                </a>
              )}
            </div>
          </div>

          {/* Warnings (including AI fallback notice) */}
          {result.warnings && result.warnings.length > 0 && (
            <div className="rounded-lg border border-amber-900/50 bg-amber-950/20 p-4 text-amber-400 text-sm flex flex-col gap-2">
              <p className="font-medium">Avisos ({result.warnings.length}):</p>
              <ul className="list-disc pl-5 flex flex-col gap-1">
                {result.warnings.map((w, idx) => (
                  <li key={idx} className="text-amber-200/80">
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
