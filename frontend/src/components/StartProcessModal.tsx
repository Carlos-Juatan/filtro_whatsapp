import React, { useState, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X, Play, AlertCircle } from 'lucide-react';
import { useKeys } from '../services/keys';
import { usePrompts } from '../services/prompts';

export interface StartProcessModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (keyId: string, promptId: string) => void;
  onOpenSettings: (tab: string) => void;
  ferramenta?: "extrator" | "gerador";
}

export const StartProcessModal: React.FC<StartProcessModalProps> = ({
  isOpen,
  onOpenChange,
  onConfirm,
  onOpenSettings,
  ferramenta
}) => {
  const { keys, loading: keysLoading } = useKeys();
  const { prompts, loading: promptsLoading } = usePrompts(ferramenta);
  
  const [selectedKey, setSelectedKey] = useState<string>('');
  const [selectedPrompt, setSelectedPrompt] = useState<string>('');

  // Auto-select first available options if not set
  useEffect(() => {
    if (keys.length > 0 && !selectedKey) {
      setSelectedKey(keys[0].id);
    }
  }, [keys, selectedKey]);

  useEffect(() => {
    if (prompts.length > 0 && !selectedPrompt) {
      setSelectedPrompt(prompts[0].id);
    }
  }, [prompts, selectedPrompt]);

  const handleConfirm = () => {
    if (selectedKey && selectedPrompt) {
      onConfirm(selectedKey, selectedPrompt);
    }
  };

  const loading = keysLoading || promptsLoading;
  const hasNoKeys = !loading && keys.length === 0;

  return (
    <Dialog.Root open={isOpen} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity" />
        <Dialog.Content className="fixed left-[50%] top-[50%] w-[90vw] max-w-[500px] translate-x-[-50%] translate-y-[-50%] rounded-xl bg-white dark:bg-gray-950 p-6 shadow-2xl focus:outline-none z-50 flex flex-col border border-gray-200 dark:border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <Dialog.Title className="text-xl font-semibold text-gray-900 dark:text-gray-100 m-0">
              Iniciar Processamento
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 focus:outline-none p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors"
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </Dialog.Close>
          </div>

          <div className="flex flex-col gap-5 py-4">
            {hasNoKeys ? (
              <div className="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 p-4 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />
                <div className="flex flex-col gap-2">
                  <p className="text-sm font-medium">Nenhuma Chave de API encontrada</p>
                  <p className="text-xs">Para processar os arquivos, você precisa configurar uma chave da OpenAI.</p>
                  <button 
                    onClick={() => {
                      onOpenChange(false);
                      onOpenSettings('keys');
                    }}
                    className="text-xs bg-red-100 hover:bg-red-200 dark:bg-red-800/40 dark:hover:bg-red-800/60 text-red-800 dark:text-red-300 font-semibold py-1.5 px-3 rounded w-fit transition-colors mt-1"
                  >
                    Adicionar Chave
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Selecione a Chave de API
                  </label>
                  <select
                    className="w-full px-3 py-2.5 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                    value={selectedKey}
                    onChange={(e) => setSelectedKey(e.target.value)}
                    disabled={loading}
                  >
                    {keys.map((k) => (
                      <option key={k.id} value={k.id}>
                        {k.nomeIdentificacao} ({k.chave.substring(0, 4)}...{k.chave.substring(k.chave.length - 4)})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Selecione o Prompt e Idioma
                  </label>
                  <select
                    className="w-full px-3 py-2.5 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                    value={selectedPrompt}
                    onChange={(e) => setSelectedPrompt(e.target.value)}
                    disabled={loading || prompts.length === 0}
                  >
                    {prompts.length === 0 && <option value="">Nenhum prompt disponível</option>}
                    {prompts.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.nome} - {p.modeloOpenAI} ({p.idiomaModelo})
                      </option>
                    ))}
                  </select>
                  {prompts.length === 0 && (
                    <button 
                      onClick={() => {
                        onOpenChange(false);
                        onOpenSettings('prompts');
                      }}
                      className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-left mt-1"
                    >
                      Configurar um prompt
                    </button>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="flex justify-end mt-2 pt-4 border-t border-gray-100 dark:border-gray-800">
            <button
              type="button"
              className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handleConfirm}
              disabled={hasNoKeys || !selectedKey || !selectedPrompt}
            >
              <Play size={16} /> Confirmar e Iniciar
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
