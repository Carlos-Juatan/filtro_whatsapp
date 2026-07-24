
import { Database, Lightbulb, Combine, Settings } from 'lucide-react';

export type ToolType = 'extrator' | 'gerador' | 'consolidador';

interface NavigationProps {
  activeTool: string;
  setActiveTool: (tool: ToolType) => void;
  onOpenSettings: (tab: string) => void;
}

export function Navigation({ activeTool, setActiveTool, onOpenSettings }: NavigationProps) {
  return (
    <>
      <header className="bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-800 sticky top-0 z-10 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-white transition-colors duration-300 ${
                activeTool === 'extrator' ? 'bg-blue-600' :
                activeTool === 'gerador' ? 'bg-emerald-600' : 'bg-purple-600'
              }`}>
                {activeTool === 'extrator' ? <Database size={18} /> :
                 activeTool === 'gerador' ? <Lightbulb size={18} /> : <Combine size={18} />}
              </div>
              <h1 className={`text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r transition-all duration-300 ${
                activeTool === 'extrator' 
                  ? 'from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400'
                  : activeTool === 'gerador'
                  ? 'from-emerald-600 to-teal-600 dark:from-emerald-400 dark:to-teal-400'
                  : 'from-purple-600 to-fuchsia-600 dark:from-purple-400 dark:to-fuchsia-400'
              }`}>
                {activeTool === 'extrator' ? 'Extrator P&R' :
                 activeTool === 'gerador' ? 'Gerador de Perguntas' : 'Consolidador P&R'}
              </h1>
            </div>

            {/* Main Navigation Tabs */}
            <div className="hidden md:flex bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
              <button
                onClick={() => setActiveTool('extrator')}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all duration-200 flex items-center gap-2 ${
                  activeTool === 'extrator'
                    ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700/50'
                }`}
              >
                <Database size={16} />
                Extrator
              </button>
              <button
                onClick={() => setActiveTool('gerador')}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all duration-200 flex items-center gap-2 ${
                  activeTool === 'gerador'
                    ? 'bg-white dark:bg-gray-700 text-emerald-600 dark:text-emerald-400 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700/50'
                }`}
              >
                <Lightbulb size={16} />
                Gerador
              </button>
              <button
                onClick={() => setActiveTool('consolidador')}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all duration-200 flex items-center gap-2 ${
                  activeTool === 'consolidador'
                    ? 'bg-white dark:bg-gray-700 text-purple-600 dark:text-purple-400 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700/50'
                }`}
              >
                <Combine size={16} />
                Consolidar
              </button>
            </div>
          </div>

          <button
            className="p-2 text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-full transition-colors"
            title="Configurações"
            aria-label="Configurações"
            onClick={() => onOpenSettings('keys')}
          >
            <Settings size={20} />
          </button>
        </div>
      </header>

      {/* Mobile Navigation Tabs (visible only on small screens) */}
      <div className="md:hidden bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 p-2 flex justify-center">
        <div className="flex bg-gray-100 dark:bg-gray-800 p-1 rounded-lg w-full max-w-md gap-1">
          <button
            onClick={() => setActiveTool('extrator')}
            className={`flex-1 px-2 py-2 text-xs font-medium rounded-md transition-all duration-200 flex flex-col justify-center items-center gap-1 ${
              activeTool === 'extrator'
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700/50'
            }`}
          >
            <Database size={16} />
            Extrator
          </button>
          <button
            onClick={() => setActiveTool('gerador')}
            className={`flex-1 px-2 py-2 text-xs font-medium rounded-md transition-all duration-200 flex flex-col justify-center items-center gap-1 ${
              activeTool === 'gerador'
                ? 'bg-white dark:bg-gray-700 text-emerald-600 dark:text-emerald-400 shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700/50'
            }`}
          >
            <Lightbulb size={16} />
            Gerador
          </button>
          <button
            onClick={() => setActiveTool('consolidador')}
            className={`flex-1 px-2 py-2 text-xs font-medium rounded-md transition-all duration-200 flex flex-col justify-center items-center gap-1 ${
              activeTool === 'consolidador'
                ? 'bg-white dark:bg-gray-700 text-purple-600 dark:text-purple-400 shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700/50'
            }`}
          >
            <Combine size={16} />
            Consolidar
          </button>
        </div>
      </div>
    </>
  );
}
