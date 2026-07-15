/**
 * Frontend API service layer.
 *
 * Provides:
 *  1. A configured Axios instance (`axiosInstance`) pointing to the backend
 *     via Vite's dev-server proxy (/api → http://localhost:8100).
 *  2. Full TypeScript type definitions that mirror the backend Pydantic schemas.
 *  3. An `ApiClient` interface that decouples consumers from the transport layer.
 *  4. A `ProductionApiClient` that implements all API operations using Axios.
 *  5. A `MockApiClient` for isolated unit/component testing (no network required).
 *  6. An `ApiClientFactory` that returns the appropriate implementation based
 *     on the runtime environment.
 */

import axios, { AxiosInstance, AxiosResponse } from "axios";

// ─────────────────────────────────────────────────────────────────────────────
// Domain Type Definitions  (mirror of backend/src/models/schemas.py)
// ─────────────────────────────────────────────────────────────────────────────

/** Supported OpenAI model identifiers. */
export type ModeloOpenAI = "gpt-4o-mini" | "gpt-4o";

/** Prompt types: system default vs. user-defined. */
export type TipoPrompt = "FIXO" | "CUSTOMIZADO";

/** File processing status machine states. */
export type StatusArquivo = "PENDENTE" | "PROCESSANDO" | "CONCLUIDO" | "ERRO";

/** Log event severity levels. */
export type TipoLog = "INFO" | "SUCESSO" | "ERRO";

/** Represents a stored OpenAI API key credential. */
export interface ChaveAPI {
  id: string;
  nomeIdentificacao: string;
  chave: string;
}

/** Request body for creating a new API key. */
export type ChaveAPICreate = Omit<ChaveAPI, "id">;

/** Represents a prompt configuration (persisted in Docker volume). */
export interface PromptConfig {
  id: string;
  nome: string;
  tipo: TipoPrompt;
  textoInstrucao?: string;
  palavrasChave: string[];
  idiomaModelo: string;
  modeloOpenAI: ModeloOpenAI;
}

/** Request body for creating or updating a prompt config. */
export type PromptConfigCreate = Omit<PromptConfig, "id" | "tipo">;

/** An extracted, grouped, and consolidated Q&A pair. */
export interface ResultadoParPR {
  perguntaPadronizada: string;
  respostaConsolidada: string;
  frequencia: number;
  metadata?: string;
  category: string;
}

/** A real-time log event emitted during file processing. */
export interface ItemLog {
  timestamp: string;
  tipo: TipoLog;
  mensagem: string;
}

/** Generic API error shape returned by the backend. */
export interface ApiError {
  detail: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// WebSocket payload types  (Client → Server)
// ─────────────────────────────────────────────────────────────────────────────

export interface FilePayload {
  nomeArquivo: string;
  conteudoBruto: string;
}

export interface WSStartMessage {
  action: "START";
  key_id: string;
  prompt_id: string;
  files: FilePayload[];
}

// ─────────────────────────────────────────────────────────────────────────────
// WebSocket event types  (Server → Client)
// ─────────────────────────────────────────────────────────────────────────────

export interface WSLogEvent {
  event: "LOG";
  data: ItemLog;
}

export interface WSChunkSuccessData {
  file_id: string;
  chunk_index: number;
  total_chunks: number;
  extracted_pairs: ResultadoParPR[];
}

export interface WSChunkSuccessEvent {
  event: "CHUNK_SUCCESS";
  data: WSChunkSuccessData;
}

export interface WSQueueErrorData {
  timestamp: string;
  mensagem: string;
  partial_results: ResultadoParPR[];
}

export interface WSQueueErrorEvent {
  event: "QUEUE_ERROR";
  data: WSQueueErrorData;
}

export interface WSQueueCompleteData {
  results: ResultadoParPR[];
}

export interface WSQueueCompleteEvent {
  event: "QUEUE_COMPLETE";
  data: WSQueueCompleteData;
}

export type WSServerEvent =
  | WSLogEvent
  | WSChunkSuccessEvent
  | WSQueueErrorEvent
  | WSQueueCompleteEvent;

// ─────────────────────────────────────────────────────────────────────────────
// Axios instance
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Shared Axios instance.
 *
 * Base URL is intentionally empty so all requests are relative to the current
 * origin. Vite's dev-server proxy rewrites `/api/*` to `http://localhost:8100`
 * during development; in production the FastAPI server handles `/api/*` directly.
 */
export const axiosInstance: AxiosInstance = axios.create({
  baseURL: "",
  timeout: 30_000, // 30 s – generous enough for LLM round-trips
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ─── Request interceptor: attach any future auth headers here ───────────────
axiosInstance.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
);

// ─── Response interceptor: normalise error shape ────────────────────────────
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail: string =
      error?.response?.data?.detail ??
      error?.message ??
      "Unknown network error";
    return Promise.reject(new Error(detail));
  },
);

// ─────────────────────────────────────────────────────────────────────────────
// ApiClient Interface  (decouples consumers from transport)
// ─────────────────────────────────────────────────────────────────────────────

export interface ApiClient {
  // API Key operations
  listKeys(): Promise<ChaveAPI[]>;
  createKey(payload: ChaveAPICreate): Promise<ChaveAPI>;
  deleteKey(id: string): Promise<void>;

  // Prompt config operations
  listPrompts(): Promise<PromptConfig[]>;
  getDefaultPromptText(): Promise<string>;
  savePrompt(payload: PromptConfigCreate): Promise<PromptConfig>;
  deletePrompt(id: string): Promise<void>;
}

// ─────────────────────────────────────────────────────────────────────────────
// ProductionApiClient  (real HTTP calls via Axios)
// ─────────────────────────────────────────────────────────────────────────────

export class ProductionApiClient implements ApiClient {
  private readonly http: AxiosInstance;

  constructor(http: AxiosInstance = axiosInstance) {
    this.http = http;
  }

  // ── API Keys ──────────────────────────────────────────────────────────────

  async listKeys(): Promise<ChaveAPI[]> {
    const res: AxiosResponse<ChaveAPI[]> = await this.http.get("/api/keys");
    return res.data;
  }

  async createKey(payload: ChaveAPICreate): Promise<ChaveAPI> {
    const res: AxiosResponse<ChaveAPI> = await this.http.post("/api/keys", payload);
    return res.data;
  }

  async deleteKey(id: string): Promise<void> {
    await this.http.delete(`/api/keys/${id}`);
  }

  // ── Prompts ───────────────────────────────────────────────────────────────

  async listPrompts(): Promise<PromptConfig[]> {
    const res: AxiosResponse<PromptConfig[]> = await this.http.get("/api/prompts");
    return res.data;
  }

  async getDefaultPromptText(): Promise<string> {
    const res: AxiosResponse<{ textoInstrucao: string }> = await this.http.get("/api/prompts/default");
    return res.data.textoInstrucao;
  }

  async savePrompt(payload: PromptConfigCreate): Promise<PromptConfig> {
    const res: AxiosResponse<PromptConfig> = await this.http.post("/api/prompts", payload);
    return res.data;
  }

  async deletePrompt(id: string): Promise<void> {
    await this.http.delete(`/api/prompts/${id}`);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// MockApiClient  (in-memory implementation for tests & Storybook)
// ─────────────────────────────────────────────────────────────────────────────

export class MockApiClient implements ApiClient {
  private keys: ChaveAPI[] = [];
  private prompts: PromptConfig[] = [
    {
      id: "mock-prompt-fixo-001",
      nome: "Filtro Padrão P&R",
      tipo: "FIXO",
      textoInstrucao:
        "Extraia perguntas e respostas do texto fornecido no formato JSON.",
      palavrasChave: [],
      idiomaModelo: "pt-br",
      modeloOpenAI: "gpt-4o-mini",
    },
  ];

  async listKeys(): Promise<ChaveAPI[]> {
    return [...this.keys];
  }

  async createKey(payload: ChaveAPICreate): Promise<ChaveAPI> {
    const existing = this.keys.find(
      (k) => k.nomeIdentificacao === payload.nomeIdentificacao,
    );
    if (existing) {
      throw new Error(
        `O nome de identificação '${payload.nomeIdentificacao}' já está em uso.`,
      );
    }
    const newKey: ChaveAPI = {
      id: `mock-key-${Date.now()}`,
      ...payload,
    };
    this.keys.push(newKey);
    return newKey;
  }

  async deleteKey(id: string): Promise<void> {
    const idx = this.keys.findIndex((k) => k.id === id);
    if (idx === -1) throw new Error("Chave de API não encontrada.");
    this.keys.splice(idx, 1);
  }

  async listPrompts(): Promise<PromptConfig[]> {
    return [...this.prompts];
  }

  async getDefaultPromptText(): Promise<string> {
    return (
      "Você é um especialista em extração e análise de conversas de atendimento ao cliente. " +
      "Sua tarefa é identificar TODAS as perguntas feitas pelos clientes e suas respectivas respostas " +
      "dadas pelo suporte no texto de conversa fornecido (exportado do WhatsApp)."
    );
  }

  async savePrompt(payload: PromptConfigCreate): Promise<PromptConfig> {
    const saved: PromptConfig = {
      id: `mock-prompt-${Date.now()}`,
      tipo: "CUSTOMIZADO",
      ...payload,
    };
    this.prompts.push(saved);
    return saved;
  }

  async deletePrompt(id: string): Promise<void> {
    const idx = this.prompts.findIndex((p) => p.id === id);
    if (idx === -1) throw new Error("Prompt não encontrado.");
    this.prompts.splice(idx, 1);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// ApiClientFactory
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Returns the appropriate ApiClient based on the runtime environment.
 *
 * Usage:
 *   const client = ApiClientFactory.getClient();          // production
 *   const client = ApiClientFactory.getClient("test");    // unit tests
 */
export class ApiClientFactory {
  static getClient(env?: string): ApiClient {
    const resolvedEnv = env ?? import.meta.env.MODE;
    if (resolvedEnv === "test") {
      return new MockApiClient();
    }
    return new ProductionApiClient(axiosInstance);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton default client (for use across React components via context/hook)
// ─────────────────────────────────────────────────────────────────────────────

/** Default API client singleton. Swap via ApiClientFactory.getClient() in tests. */
export const apiClient: ApiClient = ApiClientFactory.getClient();
