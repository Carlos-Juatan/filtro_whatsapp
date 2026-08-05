import { useState } from 'react';
import { ExtractorPanel } from './components/ExtractorPanel';
import { GeneratorPanel } from './components/GeneratorPanel';

import { SettingsModal } from './components/SettingsModal';
import { Navigation, ToolType } from './components/Navigation';
import { MergerPanel } from './components/MergerPanel';

export default function App() {
  const [activeTool, setActiveTool] = useState<ToolType>('extrator');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState('keys');

  const handleOpenSettings = (tab: string) => {
    setSettingsTab(tab);
    setIsSettingsOpen(true);
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-950 text-gray-900 dark:text-gray-100 font-sans selection:bg-blue-200 dark:selection:bg-blue-900">
      <Navigation activeTool={activeTool} setActiveTool={setActiveTool} onOpenSettings={handleOpenSettings} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid">
          {/* We keep both mounted but toggle visibility so states don't reset */}
          <div 
            className={`col-start-1 row-start-1 transition-all duration-300 ${
              activeTool === 'extrator' ? 'opacity-100 z-10 translate-y-0' : 'opacity-0 z-0 translate-y-4 pointer-events-none'
            }`}
          >
            <ExtractorPanel onOpenSettings={handleOpenSettings} />
          </div>
          <div 
            className={`col-start-1 row-start-1 transition-all duration-300 ${
              activeTool === 'gerador' ? 'opacity-100 z-10 translate-y-0' : 'opacity-0 z-0 translate-y-4 pointer-events-none'
            }`}
          >
            <GeneratorPanel onOpenSettings={handleOpenSettings} />
          </div>
          <div 
            className={`col-start-1 row-start-1 transition-all duration-300 ${
              activeTool === 'consolidador' ? 'opacity-100 z-10 translate-y-0' : 'opacity-0 z-0 translate-y-4 pointer-events-none'
            }`}
          >
            <MergerPanel />
          </div>
        </div>
      </main>

      <SettingsModal 
        isOpen={isSettingsOpen} 
        onOpenChange={setIsSettingsOpen} 
        defaultTab={settingsTab} 
      />
    </div>
  );
}
