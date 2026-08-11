import type { ChunkProgressPayload, ExtractionResult } from '../types/exactQA';

export interface ExactExtractorCallbacks {
  onLog?: (log: { message: string; timestamp?: string }) => void;
  /** Called for every chunk processed, enabling real-time progress bars (T011) */
  onChunkProgress?: (progress: ChunkProgressPayload) => void;
  onComplete?: (result: ExtractionResult) => void;
  onError?: (error: string) => void;
  onOpen?: () => void;
  onClose?: () => void;
}

export class ExactExtractorService {
  private ws: WebSocket | null = null;
  private callbacks: ExactExtractorCallbacks = {};

  public get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  public connect(callbacks: ExactExtractorCallbacks): void {
    this.callbacks = callbacks;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/exact-extractor/ws`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.callbacks.onOpen?.();
    };

    this.ws.onerror = () => {
      this.callbacks.onError?.('Erro na conexão WebSocket do Extrator Exato.');
    };

    this.ws.onclose = () => {
      this.callbacks.onClose?.();
      this.ws = null;
    };

    this.ws.onmessage = (event: MessageEvent<string>) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'log') {
          this.callbacks.onLog?.({ message: data.message, timestamp: data.timestamp });
        } else if (data.type === 'chunk_progress') {
          // T011: route chunk progress events to dedicated callback
          this.callbacks.onChunkProgress?.(data.data as ChunkProgressPayload);
        } else if (data.type === 'complete') {
          this.callbacks.onComplete?.(data.data as ExtractionResult);
        } else if (data.type === 'error') {
          this.callbacks.onError?.(data.error || 'Erro desconhecido durante processamento.');
        }
      } catch {
        console.error('Falha ao interpretar resposta do WebSocket:', event.data);
      }
    };
  }

  public startExtraction(payload: {
    filename: string;
    content: string;
    key_id?: string;
    api_key?: string;
  }): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket não está conectado.');
    }
    this.ws.send(
      JSON.stringify({
        action: 'start_extraction',
        ...payload,
      })
    );
  }

  public disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const exactExtractorService = new ExactExtractorService();
