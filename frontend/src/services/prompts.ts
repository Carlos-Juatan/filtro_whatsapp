import { useState, useEffect } from "react";
import { PromptConfig, PromptConfigCreate, apiClient, TipoFerramenta } from "./api";

export function usePrompts(ferramenta?: TipoFerramenta) {
  const [prompts, setPrompts] = useState<PromptConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [defaultPromptText, setDefaultPromptText] = useState<string | null>(null);

  const fetchPrompts = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listPrompts(ferramenta);
      setPrompts(data);
    } catch (err: any) {
      setError(err.message || "Falha ao carregar prompts");
    } finally {
      setLoading(false);
    }
  };

  const fetchDefaultPromptText = async (): Promise<string> => {
    if (defaultPromptText !== null) return defaultPromptText;
    try {
      const text = await apiClient.getDefaultPromptText();
      setDefaultPromptText(text);
      return text;
    } catch {
      return "";
    }
  };

  const addPrompt = async (payload: PromptConfigCreate) => {
    setLoading(true);
    setError(null);
    try {
      const newPrompt = await apiClient.savePrompt(payload);
      setPrompts((prev) => [...prev, newPrompt]);
      return newPrompt;
    } catch (err: any) {
      setError(err.message || "Falha ao salvar prompt");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const deletePrompt = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      await apiClient.deletePrompt(id);
      setPrompts((prev) => prev.filter((p) => p.id !== id));
    } catch (err: any) {
      setError(err.message || "Falha ao excluir prompt");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPrompts();
  }, []);

  return {
    prompts,
    loading,
    error,
    defaultPromptText,
    fetchPrompts,
    fetchDefaultPromptText,
    addPrompt,
    deletePrompt,
  };
}
