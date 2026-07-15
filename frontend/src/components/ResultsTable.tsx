import { useState, useMemo } from 'react';
import { ResultadoParPR } from '../services/api';
import { exportToJson, exportToTxt, exportToUncategorizedTxt } from '../utils/export';
import { Search, ArrowUpDown, Download, BookOpen, MessageSquare, AlertCircle } from 'lucide-react';

interface ResultsTableProps {
  results: ResultadoParPR[];
  uncategorizedContent?: string[];
}

type SortField = 'perguntaPadronizada' | 'category' | 'metadata' | 'frequencia';
type ResultsTab = 'qna' | 'uncategorized';

export function ResultsTable({ results, uncategorizedContent = [] }: ResultsTableProps) {
  const [activeTab, setActiveTab] = useState<ResultsTab>('qna');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<SortField>('frequencia');
  const [sortDesc, setSortDesc] = useState(true);

  const filteredAndSorted = useMemo(() => {
    let filtered = results.filter(r => 
      r.perguntaPadronizada.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.respostaConsolidada.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.metadata || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.category.toLowerCase().includes(searchTerm.toLowerCase())
    );

    filtered.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      // Handle fallback for category sorting if metadata is empty
      if (sortField === 'metadata') {
        aVal = a.metadata || a.category;
        bVal = b.metadata || b.category;
      }
      
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDesc ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
      } else if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDesc ? bVal - aVal : aVal - bVal;
      }
      return 0;
    });

    return filtered;
  }, [results, searchTerm, sortField, sortDesc]);

  const filteredUncategorized = useMemo(() => {
    if (!searchTerm) return uncategorizedContent;
    return uncategorizedContent.filter(item =>
      item.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [uncategorizedContent, searchTerm]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDesc(!sortDesc);
    } else {
      setSortField(field);
      setSortDesc(true);
    }
  };

  const hasResults = results.length > 0 || uncategorizedContent.length > 0;

  if (!hasResults) {
    return <div className="text-gray-500 p-8 border rounded-lg text-center bg-gray-50 dark:bg-gray-800/50">Nenhum resultado processado. Envie arquivos para ver os resultados aqui.</div>;
  }

  return (
    <div className="flex flex-col space-y-4">
      {/* Inner tab bar for Q&A vs Uncategorized */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        <button
          id="results-tab-qna"
          onClick={() => setActiveTab('qna')}
          className={`flex items-center gap-2 px-5 py-2.5 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'qna'
              ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <MessageSquare size={15} />
          Perguntas &amp; Respostas
          {results.length > 0 && (
            <span className="bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300 text-xs px-2 py-0.5 rounded-full ml-1">
              {results.length}
            </span>
          )}
        </button>
        <button
          id="results-tab-uncategorized"
          onClick={() => setActiveTab('uncategorized')}
          className={`flex items-center gap-2 px-5 py-2.5 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'uncategorized'
              ? 'border-emerald-600 text-emerald-600 dark:border-emerald-400 dark:text-emerald-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <BookOpen size={15} />
          Conteúdo Adicional / Base de Dados
          {uncategorizedContent.length > 0 && (
            <span className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300 text-xs px-2 py-0.5 rounded-full ml-1">
              {uncategorizedContent.length}
            </span>
          )}
        </button>
      </div>

      {/* Search bar + export buttons (shared) */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
          <input
            id="results-search-input"
            type="text"
            placeholder={activeTab === 'qna' ? "Buscar perguntas, respostas ou categorias..." : "Buscar conteúdo adicional..."}
            className="pl-9 pr-4 py-2 w-full border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200 border-gray-300 dark:border-gray-700"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          {activeTab === 'qna' ? (
            <>
              <button
                id="export-txt-btn"
                onClick={() => exportToTxt(filteredAndSorted)}
                className="flex-1 md:flex-none flex items-center justify-center px-4 py-2 text-sm font-medium border rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-800 dark:text-gray-200 border-gray-300 dark:border-gray-700 transition-colors bg-white dark:bg-gray-900 shadow-sm"
              >
                <Download className="h-4 w-4 mr-2" /> TXT
              </button>
              <button
                id="export-json-btn"
                onClick={() => exportToJson(filteredAndSorted)}
                className="flex-1 md:flex-none flex items-center justify-center px-4 py-2 text-sm font-medium border rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-800 dark:text-gray-200 border-gray-300 dark:border-gray-700 transition-colors bg-white dark:bg-gray-900 shadow-sm"
              >
                <Download className="h-4 w-4 mr-2" /> JSON
              </button>
            </>
          ) : (
            <button
              id="export-uncategorized-btn"
              onClick={() => exportToUncategorizedTxt(filteredUncategorized)}
              disabled={filteredUncategorized.length === 0}
              className="flex-1 md:flex-none flex items-center justify-center px-4 py-2 text-sm font-medium border rounded-md transition-colors shadow-sm
                bg-emerald-50 hover:bg-emerald-100 border-emerald-300 text-emerald-700
                dark:bg-emerald-900/20 dark:hover:bg-emerald-900/40 dark:border-emerald-700 dark:text-emerald-300
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className="h-4 w-4 mr-2" /> Baixar Conteúdo Adicional (TXT)
            </button>
          )}
        </div>
      </div>

      {/* Q&A Tab content */}
      {activeTab === 'qna' && (
        <div className="overflow-x-auto border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900 shadow-sm">
          <table className="w-full text-left text-sm text-gray-700 dark:text-gray-300">
            <thead className="bg-gray-50 dark:bg-gray-800/80 text-xs uppercase text-gray-600 dark:text-gray-400 font-semibold border-b border-gray-200 dark:border-gray-800">
              <tr>
                <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" onClick={() => handleSort('metadata')}>
                  <div className="flex items-center">Categoria <ArrowUpDown className="ml-1 h-3 w-3" /></div>
                </th>
                <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors w-1/3" onClick={() => handleSort('perguntaPadronizada')}>
                  <div className="flex items-center">Pergunta <ArrowUpDown className="ml-1 h-3 w-3" /></div>
                </th>
                <th className="px-4 py-3 w-1/2">Resposta</th>
                <th className="px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" onClick={() => handleSort('frequencia')}>
                  <div className="flex items-center justify-end">Freq. <ArrowUpDown className="ml-1 h-3 w-3" /></div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {filteredAndSorted.map((item, idx) => (
                <tr key={idx} className="hover:bg-gray-50/80 dark:hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3 align-top whitespace-nowrap">
                    <span className="px-2.5 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 text-xs rounded-full font-medium">
                      {item.metadata || item.category}
                    </span>
                  </td>
                  <td className="px-4 py-3 align-top font-medium text-gray-900 dark:text-gray-100 min-w-[200px]">{item.perguntaPadronizada}</td>
                  <td className="px-4 py-3 align-top whitespace-pre-wrap text-gray-600 dark:text-gray-400 min-w-[300px]">{item.respostaConsolidada}</td>
                  <td className="px-4 py-3 align-top text-right tabular-nums font-mono font-semibold text-gray-900 dark:text-gray-100">{item.frequencia}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredAndSorted.length === 0 && (
            <div className="p-8 text-center text-gray-500">Nenhum resultado encontrado para a busca atual.</div>
          )}
        </div>
      )}

      {/* Uncategorized Tab content */}
      {activeTab === 'uncategorized' && (
        <div className="border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900 shadow-sm overflow-hidden">
          {filteredUncategorized.length === 0 ? (
            <div className="p-10 flex flex-col items-center gap-3 text-center">
              <AlertCircle className="h-10 w-10 text-gray-300 dark:text-gray-600" />
              <p className="text-gray-500 dark:text-gray-400 font-medium">
                {uncategorizedContent.length === 0
                  ? 'Nenhum conteúdo não classificado encontrado.'
                  : 'Nenhum resultado encontrado para a busca atual.'}
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500 max-w-sm">
                Este campo contém fatos, regras de negócio, preços, horários e outras informações úteis que não se enquadram como perguntas e respostas.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-gray-800" id="uncategorized-content-list">
              {filteredUncategorized.map((item, idx) => (
                <li
                  key={idx}
                  className="px-5 py-3.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors flex items-start gap-3"
                >
                  <span className="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 flex items-center justify-center text-xs font-semibold">
                    {idx + 1}
                  </span>
                  <span className="whitespace-pre-wrap leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
