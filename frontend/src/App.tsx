import React, { useState, useCallback, useEffect } from 'react';
import { FileUploader, FileEntry } from './components/FileUploader';
import { LogViewer } from './components/LogViewer';
import { ResultsTable } from './components/ResultsTable';
import { wsClient } from './services/websocket';
import { ItemLog, ResultadoParPR, WSStartMessage } from './services/api';
import * as Tabs from '@radix-ui/react-tabs';
import { Activity, Database, Settings } from 'lucide-react';

export default function App() {
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [logs, setLogs] = useState<ItemLog[]>([]);
  const [results, setResults] = useState<ResultadoParPR[]>([]);
  const [activeTab, setActiveTab] = useState('process');

  useEffect(() => {
    // We clean up when component unmounts
    return () => {
      wsClient.disconnect();
    };
  }, []);

  const handleStartProcessing = useCallback(async () => {
    if (files.length === 0) return;
    
    // Read files content
    const filePayloads = await Promise.all(files.map(async (f) => {
      return new Promise<{ nomeArquivo: string, conteudoBruto: string }>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          resolve({
            nomeArquivo: f.file.name,
            conteudoBruto: e.target?.result as string || ''
          });
        };
        reader.onerror = reject;
        reader.readAsText(f.file);
      });
    }));

    setLogs([]);
    setResults([]);
    setIsProcessing(true);
    
    const startMsg: WSStartMessage = {
      action: "START",
      key_id: "env", // hardcoded until User Story 3
      prompt_id: "env", // hardcoded until User Story 4
      files: filePayloads
    };

    wsClient.connect({
      onLog: (log) => setLogs(prev => [...prev, log]),
      onChunkSuccess: (data) => {
        // We receive chunk success events, but we wait for final consolidated results
      },
      onQueueComplete: (data) => {
        setResults(data.results);
        setIsProcessing(false);
        setActiveTab('results'); // auto switch to results
        wsClient.disconnect();
      },
      onQueueError: (data) => {
        // Also capture partial results
        if (data.partial_results && data.partial_results.length > 0) {
          setResults(data.partial_results);
        }
        setIsProcessing(false);
        wsClient.disconnect();
      },
      onError: (err) => {
        setLogs(prev => [...prev, {
          timestamp: new Date().toLocaleTimeString(),
          tipo: 'ERRO',
          mensagem: err instanceof Error ? err.message : String(err)
        }]);
        setIsProcessing(false);
      }
    });

    wsClient.sendStart(startMsg);
    
  }, [files]);

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
          {/* Settings button will go here in Phase 5 */}
          <button className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors cursor-not-allowed opacity-50" title="Configurações (Em breve)">
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
              <Database size={16} /> Resultados {results.length > 0 && <span className="bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300 text-xs px-2 py-0.5 rounded-full">{results.length}</span>}
            </Tabs.Trigger>
          </Tabs.List>
          
          <Tabs.Content value="process" className="outline-none">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <section className="flex flex-col gap-4">
                <div className="bg-white dark:bg-gray-900 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800">
                  <h2 className="text-lg font-semibold mb-4 text-gray-800 dark:text-gray-200">Arquivos para Processar</h2>
                  <FileUploader
                    files={files}
                    onFilesChange={setFiles}
                    isProcessing={isProcessing}
                    onStartProcessing={handleStartProcessing}
                  />
                </div>
              </section>
              
              <section className="flex flex-col h-[600px]">
                <LogViewer logs={logs} />
              </section>
            </div>
          </Tabs.Content>
          
          <Tabs.Content value="results" className="outline-none">
            <ResultsTable results={results} />
          </Tabs.Content>
        </Tabs.Root>
      </main>
    </div>
  );
}
