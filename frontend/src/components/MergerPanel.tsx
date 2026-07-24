import React, { useState, useRef, useCallback } from "react";
import { UploadCloud, FileText, FileJson, X, Loader2, CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { mergeService, type MergeJobResult } from "../services/mergerService";

export function MergerPanel() {
  const [inputFormat, setInputFormat] = useState<"json" | "txt">("json");
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<MergeJobResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const acceptString = inputFormat === "json" ? ".json" : ".txt";

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!isProcessing) setDragActive(true);
  }, [isProcessing]);

  const handleDragLeave = useCallback(() => setDragActive(false), []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    if (isProcessing) return;
    const dropped = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith(acceptString));
    if (dropped.length > 0) {
      setPendingFiles(prev => {
        const names = new Set(prev.map(f => f.name));
        return [...prev, ...dropped.filter(f => !names.has(f.name))];
      });
    }
  }, [isProcessing, acceptString]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    setPendingFiles(prev => {
      const names = new Set(prev.map(f => f.name));
      return [...prev, ...selected.filter(f => !names.has(f.name))];
    });
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const handleRemove = (name: string) => {
    setPendingFiles(prev => prev.filter(f => f.name !== name));
  };

  const handleProcess = async () => {
    if (pendingFiles.length === 0) return;
    setIsProcessing(true);
    setError(null);
    setResult(null);
    try {
      const res = await mergeService.consolidateFiles(inputFormat, pendingFiles);
      setResult(res);
      setPendingFiles([]);
    } catch (err: any) {
      setError(err.message || "Erro ao processar arquivos. (API pode não estar pronta - Fase 5)");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="bg-slate-900 rounded-xl shadow-lg border border-slate-800 p-6 flex flex-col gap-6 w-full max-w-4xl mx-auto min-h-[400px]">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-slate-100 mb-2">Consolidador de P&R</h2>
        <p className="text-slate-400 text-sm">Mescle múltiplos arquivos em um único dataset sem duplicatas.</p>
      </div>

      <div className="flex flex-col gap-3">
        <label className="text-sm font-medium text-slate-300">Formato de Entrada</label>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer hover:text-white transition-colors">
            <input
              type="radio"
              name="format"
              value="json"
              checked={inputFormat === "json"}
              onChange={() => { setInputFormat("json"); setPendingFiles([]); setError(null); setResult(null); }}
              className="w-4 h-4 accent-indigo-500 bg-slate-800 border-slate-700"
            />
            <FileJson className="w-4 h-4 text-indigo-400" /> JSON (.json)
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-200 cursor-pointer hover:text-white transition-colors">
            <input
              type="radio"
              name="format"
              value="txt"
              checked={inputFormat === "txt"}
              onChange={() => { setInputFormat("txt"); setPendingFiles([]); setError(null); setResult(null); }}
              className="w-4 h-4 accent-indigo-500 bg-slate-800 border-slate-700"
            />
            <FileText className="w-4 h-4 text-indigo-400" /> TXT (.txt)
          </label>
        </div>
      </div>

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
            : "border-slate-700 bg-slate-800/40 hover:border-indigo-500/50 hover:bg-slate-800/80"
        )}
      >
        <UploadCloud className={cn("h-10 w-10 transition-all", dragActive ? "text-indigo-400 scale-110" : "text-slate-500")} />
        <div className="space-y-1">
          <p className="text-sm font-medium text-slate-300">
            {dragActive ? "Solte os arquivos aqui" : `Arraste arquivos ${acceptString} ou clique para selecionar`}
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

      {pendingFiles.length > 0 && (
        <ul className="flex flex-col gap-2 max-h-48 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-700">
          {pendingFiles.map(f => (
            <li key={f.name} className="flex items-center gap-3 rounded-lg border border-slate-700/50 bg-slate-800/30 px-3 py-2 text-sm animate-in fade-in slide-in-from-bottom-2">
              {inputFormat === "json" ? <FileJson className="h-4 w-4 shrink-0 text-slate-400" /> : <FileText className="h-4 w-4 shrink-0 text-slate-400" />}
              <span className="flex-1 truncate font-medium text-slate-300">{f.name}</span>
              {!isProcessing && (
                <button onClick={(e) => { e.stopPropagation(); handleRemove(f.name); }} className="text-slate-500 hover:text-red-400 transition-colors p-1 rounded-md hover:bg-slate-700/50">
                  <X className="w-4 h-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {!isProcessing && pendingFiles.length > 0 && (
        <button
          onClick={handleProcess}
          className="w-full rounded-xl bg-indigo-600 px-6 py-3 text-sm font-medium text-white hover:bg-indigo-500 transition-all active:scale-[0.99] shadow-lg shadow-indigo-900/20"
        >
          Consolidar {pendingFiles.length} {pendingFiles.length === 1 ? "arquivo" : "arquivos"}
        </button>
      )}

      {isProcessing && (
        <div className="flex flex-col items-center justify-center py-4 gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
          <span className="text-sm text-slate-400 animate-pulse">Enviando arquivos...</span>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-900/50 bg-red-950/20 p-4 text-red-400 text-sm flex gap-3 items-center animate-in fade-in">
          <XCircle className="w-5 h-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}
      
      {result && (
        <div className="flex flex-col gap-4 animate-in fade-in">
          <div className="rounded-lg border border-emerald-900/50 bg-emerald-950/20 p-4 text-emerald-400 text-sm flex flex-col gap-2">
            <div className="flex gap-3 items-center">
              <CheckCircle className="w-5 h-5 shrink-0" />
              <p className="font-medium">Consolidação concluída com sucesso!</p>
            </div>
            <div className="pl-8 flex flex-col gap-1 text-slate-300">
              <span>Arquivos processados: {result.total_files_processed}</span>
              <span>P&R Extraídos (Total): {result.total_qna_extracted}</span>
              <span>P&R Únicos (Mesclados): {result.total_qna_merged}</span>
            </div>
            
            <div className="pl-8 flex gap-3 mt-2">
              {result.json_output_filename && (
                <a
                  href={`/api/merger/download/${result.json_output_filename}`}
                  download
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-md transition-colors border border-slate-700"
                >
                  <FileJson className="w-4 h-4 text-indigo-400" />
                  Baixar JSON
                </a>
              )}
              {result.txt_output_filename && (
                <a
                  href={`/api/merger/download/${result.txt_output_filename}`}
                  download
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-md transition-colors border border-slate-700"
                >
                  <FileText className="w-4 h-4 text-indigo-400" />
                  Baixar TXT
                </a>
              )}
            </div>
          </div>
          
          {result.warnings && result.warnings.length > 0 && (
            <div className="rounded-lg border border-amber-900/50 bg-amber-950/20 p-4 text-amber-400 text-sm flex flex-col gap-2">
              <p className="font-medium">Avisos ({result.warnings.length}):</p>
              <ul className="list-disc pl-5 flex flex-col gap-1">
                {result.warnings.map((w, idx) => (
                  <li key={idx} className="text-amber-200/80">{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
