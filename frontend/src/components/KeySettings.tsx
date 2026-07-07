import React, { useState } from 'react';
import { useKeys } from '../services/keys';

export const KeySettings: React.FC = () => {
  const { keys, loading, error, addKey, removeKey } = useKeys();
  const [nomeIdentificacao, setNomeIdentificacao] = useState('');
  const [chave, setChave] = useState('');

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nomeIdentificacao.trim() || !chave.trim()) return;
    
    try {
      await addKey({ nomeIdentificacao: nomeIdentificacao.trim(), chave: chave.trim() });
      setNomeIdentificacao('');
      setChave('');
    } catch (err) {
      // Error handled by hook
    }
  };

  return (
    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-100 flex flex-col gap-6 w-full">
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-gray-800">Chaves de API</h2>
        <p className="text-sm text-gray-500">
          Gerencie suas chaves da OpenAI. As chaves são salvas localmente e utilizadas para processamento.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleAdd} className="flex flex-col sm:flex-row gap-4 items-end">
        <div className="flex flex-col gap-1 w-full sm:w-1/3">
          <label className="text-xs font-medium text-gray-700">Nome de Identificação</label>
          <input 
            type="text"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition"
            placeholder="Ex: Minha Chave Principal"
            value={nomeIdentificacao}
            onChange={(e) => setNomeIdentificacao(e.target.value)}
            disabled={loading}
          />
        </div>
        <div className="flex flex-col gap-1 w-full sm:w-1/2">
          <label className="text-xs font-medium text-gray-700">Chave OpenAI</label>
          <input 
            type="password"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition"
            placeholder="sk-..."
            value={chave}
            onChange={(e) => setChave(e.target.value)}
            disabled={loading}
          />
        </div>
        <button 
          type="submit"
          className="w-full sm:w-auto px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition disabled:opacity-50"
          disabled={loading || !nomeIdentificacao.trim() || !chave.trim()}
        >
          Adicionar
        </button>
      </form>

      <div className="flex flex-col border border-gray-200 rounded-lg overflow-hidden">
        {keys.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">
            Nenhuma chave configurada.
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {keys.map((k) => (
              <li key={k.id} className="p-4 flex items-center justify-between hover:bg-gray-50 transition">
                <div className="flex flex-col">
                  <span className="font-medium text-gray-800">{k.nomeIdentificacao}</span>
                  <span className="text-xs text-gray-500 font-mono">
                    {k.chave.substring(0, 4)}...{k.chave.substring(k.chave.length - 4)}
                  </span>
                </div>
                <button
                  onClick={() => removeKey(k.id)}
                  className="text-red-500 hover:text-red-700 p-2 rounded-lg hover:bg-red-50 transition"
                  disabled={loading}
                  title="Remover Chave"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
