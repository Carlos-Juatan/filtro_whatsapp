/**
 * FileUploader component – drag-and-drop file upload with status/size display
 * and a processing progress bar.
 *
 * Features:
 *  - Drag-and-drop zone accepting .txt files.
 *  - Click-to-browse fallback via hidden <input type="file">.
 *  - Upload list showing file name, size, and current status (PENDENTE /
 *    PROCESSANDO / CONCLUIDO / ERRO) with per-file status icons.
 *  - A global progress bar tracking chunks processed across all files.
 *  - Premium dark-mode aesthetic with micro-animations.
 *
 * Props:
 *   onFilesReady  – called with the File[] array when the user confirms upload.
 *   isProcessing  – when true, the upload zone is disabled and the progress
 *                   bar is shown.
 *   progress      – 0–100 integer representing overall queue progress.
 *   fileStatuses  – map of filename → status string for the upload list.
 *
 * Usage:
 *   <FileUploader
 *     onFilesReady={(files) => startProcessing(files)}
 *     isProcessing={processing}
 *     progress={progressPct}
 *     fileStatuses={statuses}
 *   />
 */

import React, { useCallback, useRef, useState } from "react";
import {
  CheckCircle,
  FileText,
  Loader2,
  UploadCloud,
  X,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { StatusArquivo } from "@/services/api";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface FileEntry {
  file: File;
  status: StatusArquivo;
}

export interface FileUploaderProps {
  /** Called when the user selects / drops files and clicks "Processar". */
  onFilesReady: (files: File[]) => void;
  /** Disables the drop zone and shows the progress bar when true. */
  isProcessing?: boolean;
  /** Overall queue progress 0–100. */
  progress?: number;
  /** Per-filename status overrides coming from WebSocket events. */
  fileStatuses?: Record<string, StatusArquivo>;
  /** Called when the user wants to remove a pending file from the list. */
  onRemoveFile?: (fileName: string) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

const STATUS_ICONS: Record<StatusArquivo, React.ReactNode> = {
  PENDENTE: (
    <span className="h-4 w-4 rounded-full border-2 border-slate-400 bg-transparent" />
  ),
  PROCESSANDO: (
    <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />
  ),
  CONCLUIDO: <CheckCircle className="h-4 w-4 text-emerald-400" />,
  ERRO: <XCircle className="h-4 w-4 text-red-400" />,
};

const STATUS_LABELS: Record<StatusArquivo, string> = {
  PENDENTE: "Aguardando",
  PROCESSANDO: "Processando…",
  CONCLUIDO: "Concluído",
  ERRO: "Erro",
};

const STATUS_TEXT_COLORS: Record<StatusArquivo, string> = {
  PENDENTE: "text-slate-400",
  PROCESSANDO: "text-indigo-400",
  CONCLUIDO: "text-emerald-400",
  ERRO: "text-red-400",
};

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export function FileUploader({
  onFilesReady,
  isProcessing = false,
  progress = 0,
  fileStatuses = {},
  onRemoveFile,
}: FileUploaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // ── Drag handlers ──────────────────────────────────────────────────────────

  const handleDragOver = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (!isProcessing) setDragActive(true);
    },
    [isProcessing]
  );

  const handleDragLeave = useCallback(() => setDragActive(false), []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragActive(false);
      if (isProcessing) return;
      const dropped = Array.from(e.dataTransfer.files).filter((f) =>
        f.name.toLowerCase().endsWith(".txt")
      );
      if (dropped.length > 0) {
        setPendingFiles((prev) => {
          const names = new Set(prev.map((f) => f.name));
          return [...prev, ...dropped.filter((f) => !names.has(f.name))];
        });
      }
    },
    [isProcessing]
  );

  // ── File input change ──────────────────────────────────────────────────────

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = Array.from(e.target.files ?? []);
      setPendingFiles((prev) => {
        const names = new Set(prev.map((f) => f.name));
        return [...prev, ...selected.filter((f) => !names.has(f.name))];
      });
      // Reset input so the same file can be re-selected
      if (inputRef.current) inputRef.current.value = "";
    },
    []
  );

  // ── Remove a pending file ──────────────────────────────────────────────────

  const handleRemove = useCallback(
    (fileName: string) => {
      setPendingFiles((prev) => prev.filter((f) => f.name !== fileName));
      onRemoveFile?.(fileName);
    },
    [onRemoveFile]
  );

  // ── Submit ─────────────────────────────────────────────────────────────────

  const handleSubmit = useCallback(() => {
    if (pendingFiles.length === 0 || isProcessing) return;
    onFilesReady(pendingFiles);
    setPendingFiles([]);
  }, [pendingFiles, isProcessing, onFilesReady]);

  // ── Merged file list (pending + active with WS status) ───────────────────

  const allFiles: Array<{ name: string; size: number; status: StatusArquivo }> =
    pendingFiles.map((f) => ({
      name: f.name,
      size: f.size,
      status: fileStatuses[f.name] ?? "PENDENTE",
    }));

  // Files actively being processed but already cleared from pending list
  const activeNames = new Set(pendingFiles.map((f) => f.name));
  Object.entries(fileStatuses).forEach(([name, status]) => {
    if (!activeNames.has(name)) {
      allFiles.push({ name, size: 0, status });
    }
  });

  return (
    <section
      id="file-uploader-section"
      aria-label="Upload de arquivos de transcrição"
      className="flex flex-col gap-4"
    >
      {/* Drop Zone */}
      <div
        id="file-drop-zone"
        role="button"
        tabIndex={isProcessing ? -1 : 0}
        aria-disabled={isProcessing}
        aria-label="Arraste arquivos .txt aqui ou clique para selecionar"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isProcessing && inputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && !isProcessing)
            inputRef.current?.click();
        }}
        className={cn(
          "relative flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-8 py-12 text-center transition-all duration-300",
          isProcessing
            ? "cursor-not-allowed border-slate-700 bg-slate-900/40 opacity-60"
            : dragActive
            ? "border-indigo-400 bg-indigo-950/40 shadow-lg shadow-indigo-900/30 scale-[1.01]"
            : "border-slate-700 bg-slate-900/60 hover:border-indigo-500 hover:bg-indigo-950/20 hover:shadow-md hover:shadow-indigo-900/20"
        )}
      >
        <UploadCloud
          className={cn(
            "h-12 w-12 transition-all duration-300",
            dragActive ? "text-indigo-400 scale-110" : "text-slate-500"
          )}
          aria-hidden
        />
        <div className="space-y-1">
          <p className="text-sm font-semibold text-slate-200">
            {dragActive
              ? "Solte os arquivos aqui"
              : "Arraste arquivos .txt ou clique para selecionar"}
          </p>
          <p className="text-xs text-slate-500">
            Apenas arquivos de texto (.txt) · Até 1 MB por arquivo
          </p>
        </div>
        <input
          ref={inputRef}
          id="file-input-hidden"
          type="file"
          accept=".txt"
          multiple
          className="sr-only"
          onChange={handleInputChange}
          aria-hidden
        />
      </div>

      {/* File list */}
      {allFiles.length > 0 && (
        <ul
          id="file-upload-list"
          aria-label="Lista de arquivos para processamento"
          className="flex flex-col gap-2"
        >
          {allFiles.map(({ name, size, status }) => (
            <li
              key={name}
              className={cn(
                "flex items-center gap-3 rounded-xl border px-4 py-3 text-sm transition-all duration-200 animate-fade-in",
                status === "ERRO"
                  ? "border-red-800/60 bg-red-950/30"
                  : status === "CONCLUIDO"
                  ? "border-emerald-800/60 bg-emerald-950/20"
                  : status === "PROCESSANDO"
                  ? "border-indigo-800/60 bg-indigo-950/20"
                  : "border-slate-700/60 bg-slate-900/40"
              )}
            >
              <FileText className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
              <span className="flex-1 truncate font-medium text-slate-200">
                {name}
              </span>
              {size > 0 && (
                <span className="shrink-0 text-xs text-slate-500">
                  {formatBytes(size)}
                </span>
              )}
              <span
                className={cn(
                  "flex shrink-0 items-center gap-1 text-xs font-medium",
                  STATUS_TEXT_COLORS[status]
                )}
                aria-label={`Status: ${STATUS_LABELS[status]}`}
              >
                {STATUS_ICONS[status]}
                <span className="hidden sm:inline">{STATUS_LABELS[status]}</span>
              </span>
              {status === "PENDENTE" && !isProcessing && (
                <button
                  type="button"
                  id={`remove-file-${name.replace(/\W/g, "-")}`}
                  aria-label={`Remover ${name} da fila`}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemove(name);
                  }}
                  className="ml-1 rounded-md p-1 text-slate-500 hover:bg-slate-700 hover:text-slate-200 transition-colors"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Progress bar */}
      {isProcessing && (
        <div
          id="processing-progress-bar"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Progresso do processamento: ${progress}%`}
          className="space-y-1.5"
        >
          <div className="flex justify-between text-xs text-slate-400">
            <span>Processando chunks…</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Submit button */}
      {!isProcessing && pendingFiles.length > 0 && (
        <button
          id="start-processing-button"
          type="button"
          aria-label={`Iniciar processamento de ${pendingFiles.length} arquivo(s)`}
          onClick={handleSubmit}
          className={cn(
            "w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-3",
            "text-sm font-semibold text-white shadow-lg shadow-indigo-900/40",
            "transition-all duration-200 hover:from-indigo-500 hover:to-violet-500",
            "hover:shadow-indigo-800/50 active:scale-[0.98] focus-visible:outline-none",
            "focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2",
            "focus-visible:ring-offset-slate-950"
          )}
        >
          Processar{" "}
          {pendingFiles.length === 1
            ? "1 arquivo"
            : `${pendingFiles.length} arquivos`}
        </button>
      )}
    </section>
  );
}

export default FileUploader;
