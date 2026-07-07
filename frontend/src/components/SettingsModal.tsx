import React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import * as Tabs from '@radix-ui/react-tabs';
import { X, Key, MessageSquare } from 'lucide-react';
import { KeySettings } from './KeySettings';
import { PromptSettings } from './PromptSettings';

export interface SettingsModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  defaultTab?: string;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onOpenChange,
  defaultTab = 'keys'
}) => {
  return (
    <Dialog.Root open={isOpen} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity" />
        <Dialog.Content className="fixed left-[50%] top-[50%] max-h-[85vh] w-[90vw] max-w-[800px] translate-x-[-50%] translate-y-[-50%] rounded-[1.5rem] bg-white dark:bg-gray-950 p-6 shadow-2xl focus:outline-none z-50 overflow-y-auto flex flex-col border border-gray-200 dark:border-gray-800">
          <div className="flex items-center justify-between mb-6">
            <Dialog.Title className="text-xl font-semibold text-gray-900 dark:text-gray-100 m-0">
              Configurações
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

          <Tabs.Root defaultValue={defaultTab} className="flex flex-col w-full h-full">
            <Tabs.List className="flex border-b border-gray-200 dark:border-gray-800 mb-6 shrink-0">
              <Tabs.Trigger
                value="keys"
                className="px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 data-[state=active]:border-b-2 data-[state=active]:border-blue-600 dark:data-[state=active]:border-blue-400 transition-colors flex items-center gap-2"
              >
                <Key size={16} /> Chaves de API
              </Tabs.Trigger>
              <Tabs.Trigger
                value="prompts"
                className="px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 data-[state=active]:text-blue-600 dark:data-[state=active]:text-blue-400 data-[state=active]:border-b-2 data-[state=active]:border-blue-600 dark:data-[state=active]:border-blue-400 transition-colors flex items-center gap-2"
              >
                <MessageSquare size={16} /> Prompts e Idiomas
              </Tabs.Trigger>
            </Tabs.List>

            <Tabs.Content value="keys" className="outline-none flex-1">
              <KeySettings />
            </Tabs.Content>

            <Tabs.Content value="prompts" className="outline-none flex-1">
              <PromptSettings />
            </Tabs.Content>
          </Tabs.Root>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
