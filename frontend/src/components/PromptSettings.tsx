import React, { useState } from 'react';
import { usePrompts } from '../services/prompts';
import { ModeloOpenAI } from '../services/api';

export const PromptSettings: React.FC = () => {
  const { prompts, loading, error, addPrompt } = usePrompts();
  const [nome, setNome] = useState('');
  const [textoInstrucao, setTextoInstrucao] = useState('');
  const [palavrasChave, setPalavrasChave] = useState('');
  const [idiomaModelo, setIdiomaModelo] = useState('pt-br');
  const [modeloOpenAI, setModeloOpenAI] = useState<ModeloOpenAI>('gpt-4o-mini');

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nome.trim() || !textoInstrucao.trim()) return;
    
    try {
      await addPrompt({
        nome: nome.trim(),
        textoInstrucao: textoInstrucao.trim(),
        palavrasChave: palavrasChave.split(',').map(p => p.trim()).filter(p => p.length > 0),
        idiomaModelo,
        modeloOpenAI
      });
      setNome('');
      setTextoInstrucao('');
      setPalavrasChave('');
    } catch (err) {
      // Error handled by hook
    }
  };

  return (
    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-100 flex flex-col gap-6 w-full">
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-gray-800">Configurações de Prompt</h2>
        <p className="text-sm text-gray-500">
          Crie e gerencie seus prompts customizados, idiomas e modelos para extração.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleAdd} className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex flex-col gap-1 w-full sm:w-1/2">
            <label className="text-xs font-medium text-gray-700">Nome do Prompt</label>
            <input 
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition"
              placeholder="Ex: Extrator Inglês Detalhado"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              disabled={loading}
            />
          </div>
          <div className="flex flex-col gap-1 w-full sm:w-1/4">
            <label className="text-xs font-medium text-gray-700">Modelo OpenAI</label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition bg-white"
              value={modeloOpenAI}
              onChange={(e) => setModeloOpenAI(e.target.value as ModeloOpenAI)}
              disabled={loading}
            >
              <option value="gpt-4o-mini">gpt-4o-mini</option>
              <option value="gpt-4o">gpt-4o</option>
            </select>
          </div>
          <div className="flex flex-col gap-1 w-full sm:w-1/4">
            <label className="text-xs font-medium text-gray-700">Idioma de Saída</label>
            <input 
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition"
              placeholder="Ex: pt-br, en-us"
              value={idiomaModelo}
              onChange={(e) => setIdiomaModelo(e.target.value)}
              disabled={loading}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1 w-full">
          <label className="text-xs font-medium text-gray-700">Palavras-Chave (separadas por vírgula)</label>
          <input 
            type="text"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition"
            placeholder="Ex: dúvidas, faq, suporte"
            value={palavrasChave}
            onChange={(e) => setPalavrasChave(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="flex flex-col gap-1 w-full">
          <label className="text-xs font-medium text-gray-700">Texto de Instrução (Min. 10 caracteres)</label>
          <textarea 
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition resize-y min-h-[100px]"
            placeholder="Instruções para o LLM extrair as perguntas e respostas..."
            value={textoInstrucao}
            onChange={(e) => setTextoInstrucao(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="flex justify-end">
          <button 
            type="submit"
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition disabled:opacity-50"
            disabled={loading || !nome.trim() || textoInstrucao.trim().length < 10}
          >
            Salvar Prompt
          </button>
        </div>
      </form>

      <div className="flex flex-col border border-gray-200 rounded-lg overflow-hidden">
        {prompts.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">
            Nenhum prompt configurado.
          </div>
        ) : (
          <ul className="divide-y divide-gray-200 max-h-[300px] overflow-y-auto">
            {prompts.map((p) => (
              <li key={p.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between hover:bg-gray-50 transition gap-4">
                <div className="flex flex-col">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-800">{p.nome}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${p.tipo === 'FIXO' ? 'bg-purple-100 text-purple-700' : 'bg-green-100 text-green-700'}`}>
                      {p.tipo}
                    </span>
                  </div>
                  <div className="flex gap-4 mt-1">
                    <span className="text-xs text-gray-500 font-mono">Modelo: {p.modeloOpenAI}</span>
                    <span className="text-xs text-gray-500 font-mono">Idioma: {p.idiomaModelo}</span>
                  </div>
                  {p.palavrasChave && p.palavrasChave.length > 0 && (
                    <span className="text-xs text-gray-500 mt-1">Palavras: {p.palavrasChave.join(', ')}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
