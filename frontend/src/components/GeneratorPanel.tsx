import { useState, useCallback, useEffect } from 'react';
import { FileUploader } from './FileUploader';
import { LogViewer } from './LogViewer';
import { ResultsTable } from './ResultsTable';
import { StartProcessModal } from './StartProcessModal';
import { wsClient } from '../services/websocket';
import { ItemLog, ResultadoParPR, WSStartMessage } from '../services/api';
import * as Tabs from '@radix-ui/react-tabs';
import { Database, Lightbulb } from 'lucide-react';

interface GeneratorPanelProps {
  onOpenSettings: (tab: string) => void;
}

export function GeneratorPanel({ onOpenSettings }: GeneratorPanelProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [logs, setLogs] = useState<ItemLog[]>([]);
  const [results, setResults] = useState<ResultadoParPR[]>([]);
  const [activeTab, setActiveTab] = useState('process');
  
  const [isStartModalOpen, setIsStartModalOpen] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);

  useEffect(() => {
    // Clean up when component unmounts
    return () => {
      wsClient.disconnect();
    };
  }, []);

  const handleFilesReady = useCallback((files: File[]) => {
    if (files.length === 0) return;
    setPendingFiles(files);
    setIsStartModalOpen(true);
  }, []);

  const handleStartProcess = useCallback(async (keyId: string, promptId: string) => {
    setIsStartModalOpen(false);
    
    // Read files content
    const filePayloads = await Promise.all(pendingFiles.map((f) =>
      new Promise<{ nomeArquivo: string; conteudoBruto: string }>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          resolve({
            nomeArquivo: f.name,
            conteudoBruto: e.target?.result as string || ''
          });
        };
        reader.onerror = reject;
        reader.readAsText(f);
      })
    ));

    setLogs([]);
    setResults([]);
    setIsProcessing(true);

    const startMsg: WSStartMessage = {
      action: 'START',
      key_id: keyId,
      prompt_id: promptId,
      files: filePayloads
    };

    wsClient.connect({
      onOpen: () => {
        // WebSocket handshake complete — safe to send now
        wsClient.send(startMsg);
      },
      onLog: (log) => setLogs(prev => [...prev, log]),
      onChunkSuccess: (_data) => {
        // chunk events received – full results arrive with onComplete
      },
      onComplete: (data) => {
        setResults(data.results);
        setIsProcessing(false);
        setActiveTab('results'); // auto-switch to results tab
        wsClient.disconnect();
      },
      onError: (data) => {
        // Capture any partial results on error
        if (data.partial_results && data.partial_results.length > 0) {
          setResults(data.partial_results);
        }
        setLogs(prev => [...prev, {
          timestamp: data.timestamp,
          tipo: 'ERRO',
          mensagem: data.mensagem
        }]);
        setIsProcessing(false);
        wsClient.disconnect();
      },
      onConnectionError: (_event) => {
        setLogs(prev => [...prev, {
          timestamp: new Date().toLocaleTimeString('pt-BR', { hour12: false }),
          tipo: 'ERRO',
          mensagem: 'Falha na conexão WebSocket. Verifique se o servidor está em execução.'
        }]);
        setIsProcessing(false);
      },
    }, '/api/generate'); // Specify the new endpoint for generator
  }, [pendingFiles]);

  return (
    <div className="w-full">
      <Tabs.Root value={activeTab} onValueChange={setActiveTab} className="flex flex-col w-full">
        <Tabs.List className="flex border-b border-gray-200 dark:border-gray-800 mb-6">
          <Tabs.Trigger
            value="process"
            className="px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 data-[state=active]:text-emerald-600 dark:data-[state=active]:text-emerald-400 data-[state=active]:border-b-2 data-[state=active]:border-emerald-600 dark:data-[state=active]:border-emerald-400 transition-colors flex items-center gap-2"
          >
            <Lightbulb size={16} /> Geração
          </Tabs.Trigger>
          <Tabs.Trigger
            value="results"
            className="px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 data-[state=active]:text-emerald-600 dark:data-[state=active]:text-emerald-400 data-[state=active]:border-b-2 data-[state=active]:border-emerald-600 dark:data-[state=active]:border-emerald-400 transition-colors flex items-center gap-2"
          >
            <Database size={16} /> Resultados{' '}
            {results.length > 0 && (
              <span className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300 text-xs px-2 py-0.5 rounded-full">
                {results.length}
              </span>
            )}
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="process" className="outline-none">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <section className="flex flex-col gap-4">
              <div className="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800">
                <div className="mb-4">
                  <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                    Gerador de Perguntas
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    Faça upload de arquivos de texto (.txt) contendo fatos, regras de negócio ou informações brutas. A IA irá gerar perguntas e utilizar os fatos como respostas.
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
          {/* Note: Uncategorized content is always empty from the /api/generate endpoint per the contract */}
          <ResultsTable results={results} uncategorizedContent={[]} />
        </Tabs.Content>
      </Tabs.Root>

      <StartProcessModal 
        isOpen={isStartModalOpen} 
        onOpenChange={setIsStartModalOpen} 
        onConfirm={handleStartProcess}
        onOpenSettings={onOpenSettings}
        ferramenta="gerador"
      />
    </div>
  );
}
