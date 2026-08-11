import { useState, useCallback, useEffect } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { Layers, Database, FileText, Code, CheckCircle, AlertCircle } from 'lucide-react';
import { FileUploader } from './FileUploader';
import { LogViewer } from './LogViewer';
import { exactExtractorService } from '../services/exactExtractorService';
import type { ExtractionResult, ExactQAPair } from '../types/exactQA';
import { exportExactQAPairsToTxt, exportExactQAPairsToJson, downloadFile } from '../utils/exactExporters';
import { ItemLog } from '../services/api';

export function ExactExtractorPanel() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [logs, setLogs] = useState<ItemLog[]>([]);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [activeTab, setActiveTab] = useState('process');


  useEffect(() => {
    return () => {
      exactExtractorService.disconnect();
    };
  }, []);

  const handleFilesReady = useCallback(async (files: File[]) => {
    if (files.length === 0) return;
    const file = files[0];
    setLogs([]);
    setResult(null);
    setIsProcessing(true);


    const reader = new FileReader();
    reader.onload = (e) => {
      const content = (e.target?.result as string) || '';

      exactExtractorService.connect({
        onOpen: () => {
          exactExtractorService.startExtraction({
            filename: file.name,
            content: content,
          });
        },
        onLog: (logItem) => {
          setLogs((prev) => [
            ...prev,
            {
              timestamp: logItem.timestamp || new Date().toLocaleTimeString('pt-BR', { hour12: false }),
              tipo: 'INFO',
              mensagem: logItem.message,
            },
          ]);
        },
        onComplete: (extractionResult) => {
          setResult(extractionResult);
          setIsProcessing(false);
          setActiveTab('results');
          exactExtractorService.disconnect();
        },
        onError: (errMessage) => {
          setLogs((prev) => [
            ...prev,
            {
              timestamp: new Date().toLocaleTimeString('pt-BR', { hour12: false }),
              tipo: 'ERRO',
              mensagem: errMessage,
            },
          ]);
          setIsProcessing(false);
          exactExtractorService.disconnect();
        },
        onClose: () => {
          setIsProcessing(false);
        },
      });
    };

    reader.readAsText(file);
  }, []);

  const handleDownloadTxt = () => {
    if (!result) return;
    const txtContent = exportExactQAPairsToTxt(result);
    const baseName = result.filename.replace(/\.[^/.]+$/, '');
    downloadFile(txtContent, `${baseName}_extracao_exata.txt`, 'text/plain;charset=utf-8');
  };

  const handleDownloadJson = () => {
    if (!result) return;
    const jsonContent = exportExactQAPairsToJson(result);
    const baseName = result.filename.replace(/\.[^/.]+$/, '');
    downloadFile(jsonContent, `${baseName}_extracao_exata.json`, 'application/json');
  };

  return (
    <div className="w-full">
      <Tabs.Root value={activeTab} onValueChange={setActiveTab} className="flex flex-col w-full">
        <Tabs.List className="flex border-b border-gray-200 dark:border-gray-800 mb-6">
          <Tabs.Trigger
            value="process"
            className="px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 data-[state=active]:text-emerald-600 dark:data-[state=active]:text-emerald-400 data-[state=active]:border-b-2 data-[state=active]:border-emerald-600 dark:data-[state=active]:border-emerald-400 transition-colors flex items-center gap-2"
          >
            <Layers size={16} /> Extração Exata
          </Tabs.Trigger>
          <Tabs.Trigger
            value="results"
            className="px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 data-[state=active]:text-emerald-600 dark:data-[state=active]:text-emerald-400 data-[state=active]:border-b-2 data-[state=active]:border-emerald-600 dark:data-[state=active]:border-emerald-400 transition-colors flex items-center gap-2"
          >
            <Database size={16} /> Resultados Extraídos{' '}
            {result && result.pairs.length > 0 && (
              <span className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300 text-xs px-2 py-0.5 rounded-full font-semibold">
                {result.pairs.length}
              </span>
            )}
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="process" className="outline-none">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <section className="flex flex-col gap-4">
              <div className="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800">
                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                      Extração Exata P&R
                    </h2>
                    <span className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs px-2 py-0.5 rounded border border-emerald-500/20 font-medium">
                      Fidelidade 100%
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Selecione o arquivo de conversa exportado do WhatsApp (.txt). As perguntas e respostas serão isoladas preservando o texto original caractere por caractere.
                  </p>
                </div>
                <FileUploader
                  onFilesReady={handleFilesReady}
                  isProcessing={isProcessing}
                />
              </div>
            </section>

            <section className="flex flex-col h-[600px]">
              <LogViewer
                logs={logs}
                onClear={() => setLogs([])}
                maxHeight="540px"
              />
            </section>
          </div>
        </Tabs.Content>

        <Tabs.Content value="results" className="outline-none">
          {result ? (
            <div className="flex flex-col gap-6">
              {/* Metric Header */}
              <div className="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="text-base font-semibold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                    <CheckCircle className="text-emerald-500" size={18} />
                    Resumo do Processamento: {result.filename}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {result.total_messages_parsed} mensagens analisadas • {result.total_pairs_extracted} pares de P&R identificados
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={handleDownloadTxt}
                    className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium shadow-sm transition-colors"
                  >
                    <FileText size={16} /> Exportar TXT
                  </button>
                  <button
                    onClick={handleDownloadJson}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-700 text-white rounded-lg text-sm font-medium shadow-sm transition-colors"
                  >
                    <Code size={16} /> Exportar JSON
                  </button>
                </div>
              </div>

              {/* QA Pairs Cards List */}
              <div className="flex flex-col gap-4">
                {result.pairs.length === 0 ? (
                  <div className="bg-white dark:bg-gray-900 p-8 rounded-xl border border-gray-200 dark:border-gray-800 text-center">
                    <AlertCircle className="mx-auto text-amber-500 mb-2" size={28} />
                    <p className="text-gray-600 dark:text-gray-300 font-medium">Nenhum par de pergunta e resposta foi encontrado nesta conversa.</p>
                  </div>
                ) : (
                  result.pairs.map((pair: ExactQAPair, idx: number) => (
                    <div
                      key={pair.id}
                      className="bg-white dark:bg-gray-900 rounded-xl p-5 border border-gray-200 dark:border-gray-800 shadow-sm flex flex-col gap-3 transition-all hover:border-emerald-500/40"
                    >
                      <div className="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-800 pb-2">
                        <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                          PAR #{idx + 1} • {pair.id}
                        </span>
                        <span>ID Pergunta: {pair.question_id} | ID Resposta: {pair.answer_id}</span>
                      </div>

                      {/* Pergunta */}
                      <div className="bg-emerald-500/5 dark:bg-emerald-950/20 border border-emerald-500/20 rounded-lg p-3.5">
                        <div className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 mb-1 flex items-center justify-between">
                          <span>PERGUNTA {pair.metadata?.question_sender ? `(${pair.metadata.question_sender})` : ''}</span>
                          {pair.metadata?.question_timestamp && <span>{pair.metadata.question_timestamp}</span>}
                        </div>
                        <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap font-sans">
                          {pair.question_text}
                        </p>
                      </div>

                      {/* Resposta */}
                      <div className="bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-700/50 rounded-lg p-3.5">
                        <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1 flex items-center justify-between">
                          <span>RESPOSTA {pair.metadata?.answer_sender ? `(${pair.metadata.answer_sender})` : ''}</span>
                          {pair.metadata?.answer_timestamp && <span>{pair.metadata.answer_timestamp}</span>}
                        </div>
                        <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap font-sans">
                          {pair.answer_text}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-900 p-12 rounded-xl border border-gray-200 dark:border-gray-800 text-center">
              <Database className="mx-auto text-gray-400 mb-3" size={36} />
              <h3 className="text-base font-semibold text-gray-700 dark:text-gray-300">Nenhum resultado processado ainda</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-md mx-auto">
                Faça upload de uma conversa no formato .txt na aba "Extração Exata" para visualizar os pares extraídos.
              </p>
            </div>
          )}
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
