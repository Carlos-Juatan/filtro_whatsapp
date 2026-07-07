import { useState, useEffect } from "react";
import { PromptConfig, PromptConfigCreate, apiClient } from "./api";

export function usePrompts() {
  const [prompts, setPrompts] = useState<PromptConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPrompts = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listPrompts();
      setPrompts(data);
    } catch (err: any) {
      setError(err.message || "Falha ao carregar prompts");
    } finally {
      setLoading(false);
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

  useEffect(() => {
    fetchPrompts();
  }, []);

  return { prompts, loading, error, fetchPrompts, addPrompt };
}
