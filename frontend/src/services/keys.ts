import { useState, useEffect } from "react";
import { ChaveAPI, ChaveAPICreate, apiClient } from "./api";

export function useKeys() {
  const [keys, setKeys] = useState<ChaveAPI[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listKeys();
      setKeys(data);
    } catch (err: any) {
      setError(err.message || "Falha ao carregar chaves");
    } finally {
      setLoading(false);
    }
  };

  const addKey = async (payload: ChaveAPICreate) => {
    setLoading(true);
    setError(null);
    try {
      const newKey = await apiClient.createKey(payload);
      setKeys((prev) => [...prev, newKey]);
      return newKey;
    } catch (err: any) {
      setError(err.message || "Falha ao criar chave");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const removeKey = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      await apiClient.deleteKey(id);
      setKeys((prev) => prev.filter((k) => k.id !== id));
    } catch (err: any) {
      setError(err.message || "Falha ao remover chave");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  return { keys, loading, error, fetchKeys, addKey, removeKey };
}
