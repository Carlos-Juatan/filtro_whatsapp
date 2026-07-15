import { useState, useCallback, useEffect } from 'react';
import { FileUploader } from './components/FileUploader';
import { LogViewer } from './components/LogViewer';
import { ResultsTable } from './components/ResultsTable';
import { wsClient } from './services/websocket';
import { ItemLog, ResultadoParPR, WSStartMessage } from './services/api';
import * as Tabs from '@radix-ui/react-tabs';
import { Activity, Database, Settings } from 'lucide-react';
import { SettingsModal } from './components/SettingsModal';
import { StartProcessModal } from './components/StartProcessModal';

export default function App() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [logs, setLogs] = useState<ItemLog[]>([]);
  const [results, setResults] = useState<ResultadoParPR[]>([]);
  const [activeTab, setActiveTab] = useState('process');
  
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState('keys');
  const [isStartModalOpen, setIsStartModalOpen] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);

  useEffect(() => {
    // We clean up when component unmounts
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
    });
  }, [pendingFiles]);

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-950 text-gray-900 dark:text-gray-100 font-sans selection:bg-blue-200 dark:selection:bg-blue-900">
      <header className="bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-800 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
              <Database size={18} />
            </div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400">
              Extrator P&R
            </h1>
          </div>
          <button
            className="p-2 text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-full transition-colors"
            title="Configurações"
            aria-label="Configurações"
            onClick={() => {
              setSettingsTab('keys');
              setIsSettingsOpen(true);
            }}
          >
            <Settings size={20} />
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs.Root value={activeTab} onValueChange={setActiveTab} className="flex flex-col w-full">
          <Tabs.List className="flex border-b border-gray-200 dark:border-gray-800 mb-6">
            <Tabs.Trigger
              value="process"
              className="px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 data-[state=active]:border-b-2 data-[state=active]:border-blue-600 dark:data-[state=active]:border-blue-400 transition-colors flex items-center gap-2"
            >
              <Activity size={16} /> Processamento
            </Tabs.Trigger>
            <Tabs.Trigger
              value="results"
              className="px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 data-[state=active]:border-b-2 data-[state=active]:border-blue-600 dark:data-[state=active]:border-blue-400 transition-colors flex items-center gap-2"
            >
              <Database size={16} /> Resultados{' '}
              {results.length > 0 && (
                <span className="bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300 text-xs px-2 py-0.5 rounded-full">
                  {results.length}
                </span>
              )}
            </Tabs.Trigger>
          </Tabs.List>

          <Tabs.Content value="process" className="outline-none">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <section className="flex flex-col gap-4">
                <div className="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800">
                  <h2 className="text-lg font-semibold mb-4 text-gray-800 dark:text-gray-200">
                    Arquivos para Processar
                  </h2>
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
            <ResultsTable results={results} />
          </Tabs.Content>
        </Tabs.Root>
      </main>

      <SettingsModal 
        isOpen={isSettingsOpen} 
        onOpenChange={setIsSettingsOpen} 
        defaultTab={settingsTab} 
      />

      <StartProcessModal 
        isOpen={isStartModalOpen} 
        onOpenChange={setIsStartModalOpen} 
        onConfirm={handleStartProcess}
        onOpenSettings={(tab) => {
          setSettingsTab(tab);
          setIsSettingsOpen(true);
        }}
      />
    </div>
  );
}
