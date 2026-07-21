import React, { useState } from 'react';
import { Copy, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import { usePrompts } from '../services/prompts';
import { ModeloOpenAI } from '../services/api';

const DEFAULT_PROMPT_ID = '00000000-0000-0000-0000-000000000001';

export const PromptSettings: React.FC = () => {
  const { prompts, loading, error, addPrompt, deletePrompt, fetchDefaultPromptText } = usePrompts();
  const [nome, setNome] = useState('');
  const [textoInstrucao, setTextoInstrucao] = useState('');
  const [palavrasChave, setPalavrasChave] = useState('');
  const [idiomaModelo, setIdiomaModelo] = useState('pt-br');
  const [modeloOpenAI, setModeloOpenAI] = useState<ModeloOpenAI>('gpt-4o-mini');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nome.trim() || !textoInstrucao.trim()) return;

    try {
      await addPrompt({
        nome: nome.trim(),
        textoInstrucao: textoInstrucao.trim(),
        palavrasChave: palavrasChave.split(',').map(p => p.trim()).filter(p => p.length > 0),
        idiomaModelo,
        modeloOpenAI,
        ferramenta: 'extrator'
      });
      setNome('');
      setTextoInstrucao('');
      setPalavrasChave('');
    } catch {
      // Error handled by hook
    }
  };

  const handleDuplicateDefault = async () => {
    const text = await fetchDefaultPromptText();
    setTextoInstrucao(text);
    setNome('Cópia do Padrão');
    document.getElementById('prompt-nome-input')?.focus();
  };

  const handleDelete = async (id: string) => {
    if (deleteConfirmId !== id) {
      setDeleteConfirmId(id);
      return;
    }
    try {
      await deletePrompt(id);
    } catch {
      // Error handled by hook
    } finally {
      setDeleteConfirmId(null);
    }
  };

  return (
    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-100 flex flex-col gap-6 w-full">
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-gray-800">Configurações de Prompt</h2>
        <p className="text-sm text-gray-500">
          O prompt padrão já está disponível. Crie versões customizadas para diferentes contextos.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Prompt list */}
      <div className="flex flex-col border border-gray-200 rounded-lg overflow-hidden">
        {prompts.length === 0 && loading ? (
          <div className="p-6 text-center text-gray-400 text-sm">Carregando…</div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {prompts.map((p) => {
              const isDefault = p.id === DEFAULT_PROMPT_ID;
              const isExpanded = expandedId === p.id;
              const isConfirming = deleteConfirmId === p.id;

              return (
                <li key={p.id} className="flex flex-col">
                  <div className="p-4 flex items-center justify-between hover:bg-gray-50 transition gap-3">
                    <div className="flex flex-col flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-gray-800 truncate">{p.nome}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium shrink-0 ${
                          p.tipo === 'FIXO'
                            ? 'bg-purple-100 text-purple-700'
                            : 'bg-green-100 text-green-700'
                        }`}>
                          {p.tipo === 'FIXO' ? 'Padrão' : 'Customizado'}
                        </span>
                      </div>
                      <div className="flex gap-4 mt-1 flex-wrap">
                        <span className="text-xs text-gray-500 font-mono">Modelo: {p.modeloOpenAI}</span>
                        <span className="text-xs text-gray-500 font-mono">Idioma: {p.idiomaModelo}</span>
                      </div>
                      {p.palavrasChave && p.palavrasChave.length > 0 && (
                        <span className="text-xs text-gray-500 mt-1">
                          Palavras-chave: {p.palavrasChave.join(', ')}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {isDefault && (
                        <button
                          type="button"
                          title="Duplicar como customizado"
                          onClick={handleDuplicateDefault}
                          className="p-1.5 text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded transition"
                        >
                          <Copy size={15} />
                        </button>
                      )}
                      {!isDefault && (
                        isConfirming ? (
                          <div className="flex items-center gap-1">
                            <span className="text-xs text-red-600">Confirmar?</span>
                            <button
                              type="button"
                              onClick={() => handleDelete(p.id)}
                              className="text-xs px-2 py-0.5 bg-red-600 text-white rounded hover:bg-red-700 transition"
                            >
                              Sim
                            </button>
                            <button
                              type="button"
                              onClick={() => setDeleteConfirmId(null)}
                              className="text-xs px-2 py-0.5 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition"
                            >
                              Não
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            title="Excluir prompt"
                            onClick={() => handleDelete(p.id)}
                            disabled={loading}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition disabled:opacity-50"
                          >
                            <Trash2 size={15} />
                          </button>
                        )
                      )}
                      <button
                        type="button"
                        title={isExpanded ? 'Ocultar instrução' : 'Ver instrução'}
                        onClick={() => setExpandedId(isExpanded ? null : p.id)}
                        className="p-1.5 text-gray-400 hover:text-gray-600 rounded transition"
                      >
                        {isExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                      </button>
                    </div>
                  </div>

                  {isExpanded && p.textoInstrucao && (
                    <div className="px-4 pb-4">
                      <pre className="text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded p-3 whitespace-pre-wrap break-words max-h-48 overflow-y-auto font-sans leading-relaxed">
                        {p.textoInstrucao}
                      </pre>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Create new prompt form */}
      <div className="border-t border-gray-200 pt-4">
        <h3 className="text-base font-semibold text-gray-700 mb-4">Criar Prompt Customizado</h3>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 flex items-start gap-2">
          <Copy size={14} className="text-blue-500 mt-0.5 shrink-0" />
          <p className="text-xs text-blue-700">
            Clique no ícone <strong>Duplicar</strong> do "Padrão do Sistema" acima para pré-preencher o formulário com o texto padrão e depois personalizá-lo.
          </p>
        </div>

        <form onSubmit={handleAdd} className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex flex-col gap-1 w-full sm:w-1/2">
              <label className="text-xs font-medium text-gray-700">Nome do Prompt</label>
              <input
                id="prompt-nome-input"
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
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition resize-y min-h-[120px] font-mono text-sm"
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
      </div>
    </div>
  );
};
