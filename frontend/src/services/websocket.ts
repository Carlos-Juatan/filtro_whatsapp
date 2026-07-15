/**
 * WebSocket client service for real-time Q&A extraction processing.
 *
 * Wraps the native browser WebSocket API to provide:
 *  1. Typed event callbacks matching the server protocol (contracts/api.md §2).
 *  2. Automatic URL resolution (ws:// in dev, wss:// in production via window.location).
 *  3. A clean connect/disconnect lifecycle with error handling.
 *  4. A MockWebSocketClient for isolated component testing (no network required).
 *  5. A WebSocketClientFactory for environment-aware instantiation.
 *
 * Usage:
 *   const client = WebSocketClientFactory.getClient();
 *   client.connect({
 *     onLog: (item) => ...,
 *     onChunkSuccess: (data) => ...,
 *     onComplete: (results) => ...,
 *     onError: (data) => ...,
 *   });
 *   client.send({ action: 'START', key_id: '...', prompt_id: '...', files: [...] });
 *   // later:
 *   client.disconnect();
 */

import type {
  ItemLog,
  ResultadoParPR,
  WSChunkSuccessData,
  WSQueueCompleteData,
  WSQueueErrorData,
  WSServerEvent,
  WSStartMessage,
} from "./api";

// ─────────────────────────────────────────────────────────────────────────────
// Event callback types
// ─────────────────────────────────────────────────────────────────────────────

export interface WebSocketCallbacks {
  /** Fired for every LOG event streamed by the server. */
  onLog?: (item: ItemLog) => void;
  /** Fired when a chunk has been successfully processed. */
  onChunkSuccess?: (data: WSChunkSuccessData) => void;
  /** Fired when the entire queue completes successfully. */
  onComplete?: (data: WSQueueCompleteData) => void;
  /** Fired when the queue halts due to an unrecoverable error. */
  onError?: (data: WSQueueErrorData) => void;
  /** Fired when the WebSocket connection itself errors (not an API error). */
  onConnectionError?: (event: Event) => void;
  /** Fired when the WebSocket connection is closed. */
  onClose?: (event: CloseEvent) => void;
  /** Fired when the WebSocket connection is established. */
  onOpen?: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// WebSocketClient interface
// ─────────────────────────────────────────────────────────────────────────────

export interface WebSocketClient {
  /**
   * Open the WebSocket connection and register event callbacks.
   * Calling connect() while already connected is a no-op.
   */
  connect(callbacks: WebSocketCallbacks): void;

  /**
   * Send a message to the server (must be called after connect()).
   */
  send(message: WSStartMessage): void;

  /**
   * Close the WebSocket connection gracefully.
   */
  disconnect(): void;

  /** True if the underlying WebSocket is currently open. */
  readonly isConnected: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// URL resolver
// ─────────────────────────────────────────────────────────────────────────────

function resolveWebSocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  // In dev the Vite proxy rewrites /api/* to localhost:8100.
  // We use the current host so it works transparently in both dev and prod.
  return `${protocol}//${window.location.host}/api/process`;
}

// ─────────────────────────────────────────────────────────────────────────────
// ProductionWebSocketClient
// ─────────────────────────────────────────────────────────────────────────────

export class ProductionWebSocketClient implements WebSocketClient {
  private ws: WebSocket | null = null;
  private callbacks: WebSocketCallbacks = {};

  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  connect(callbacks: WebSocketCallbacks): void {
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      // Already connecting or connected — update callbacks only
      this.callbacks = callbacks;
      return;
    }

    this.callbacks = callbacks;
    const url = resolveWebSocketUrl();
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.callbacks.onOpen?.();
    };

    this.ws.onerror = (event) => {
      this.callbacks.onConnectionError?.(event);
    };

    this.ws.onclose = (event) => {
      this.callbacks.onClose?.(event);
      this.ws = null;
    };

    this.ws.onmessage = (event: MessageEvent<string>) => {
      this._handleMessage(event.data);
    };
  }

  send(message: WSStartMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error(
        "WebSocket is not connected. Call connect() before send()."
      );
    }
    this.ws.send(JSON.stringify(message));
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, "Client disconnected");
      this.ws = null;
    }
  }

  private _handleMessage(raw: string): void {
    let parsed: WSServerEvent;
    try {
      parsed = JSON.parse(raw) as WSServerEvent;
    } catch {
      console.error("[WebSocketClient] Failed to parse server message:", raw);
      return;
    }

    switch (parsed.event) {
      case "LOG":
        this.callbacks.onLog?.(parsed.data);
        break;
      case "CHUNK_SUCCESS":
        this.callbacks.onChunkSuccess?.(parsed.data);
        break;
      case "QUEUE_COMPLETE":
        this.callbacks.onComplete?.(parsed.data);
        break;
      case "QUEUE_ERROR":
        this.callbacks.onError?.(parsed.data);
        break;
      default:
        console.warn("[WebSocketClient] Unknown event type:", (parsed as { event: string }).event);
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// MockWebSocketClient (for testing – no network required)
// ─────────────────────────────────────────────────────────────────────────────

export class MockWebSocketClient implements WebSocketClient {
  private _connected = false;
  private _callbacks: WebSocketCallbacks = {};

  /** Expose last sent message for test assertions. */
  public lastSentMessage: WSStartMessage | null = null;

  get isConnected(): boolean {
    return this._connected;
  }

  connect(callbacks: WebSocketCallbacks): void {
    this._callbacks = callbacks;
    this._connected = true;
    // Simulate async open
    setTimeout(() => this._callbacks.onOpen?.(), 0);
  }

  send(message: WSStartMessage): void {
    if (!this._connected) {
      throw new Error("MockWebSocketClient: not connected.");
    }
    this.lastSentMessage = message;
  }

  disconnect(): void {
    this._connected = false;
    setTimeout(
      () =>
        this._callbacks.onClose?.(
          new CloseEvent("close", { code: 1000, reason: "mock disconnect" })
        ),
      0
    );
  }

  // ── Test helpers ──────────────────────────────────────────────────────────

  /** Simulate the server sending a LOG event. */
  simulateLog(item: ItemLog): void {
    this._callbacks.onLog?.(item);
  }

  /** Simulate a CHUNK_SUCCESS event. */
  simulateChunkSuccess(data: WSChunkSuccessData): void {
    this._callbacks.onChunkSuccess?.(data);
  }

  /** Simulate a QUEUE_COMPLETE event. */
  simulateComplete(results: ResultadoParPR[], uncategorized_database_content: string[] = []): void {
    this._callbacks.onComplete?.({ results, uncategorized_database_content });
  }

  /** Simulate a QUEUE_ERROR event. */
  simulateError(mensagem: string, partial_results: ResultadoParPR[] = [], uncategorized_database_content: string[] = []): void {
    this._callbacks.onError?.({
      timestamp: new Date().toISOString().slice(11, 19),
      mensagem,
      partial_results,
      uncategorized_database_content,
    });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// WebSocketClientFactory
// ─────────────────────────────────────────────────────────────────────────────

export class WebSocketClientFactory {
  /**
   * Return the appropriate WebSocket client based on the runtime environment.
   *
   * @param env Optional override: 'test' returns a MockWebSocketClient.
   *             Defaults to `import.meta.env.MODE`.
   */
  static getClient(env?: string): WebSocketClient {
    const resolvedEnv = env ?? import.meta.env.MODE;
    if (resolvedEnv === "test") {
      return new MockWebSocketClient();
    }
    return new ProductionWebSocketClient();
  }
}

/** Default singleton WebSocket client. */
export const wsClient: WebSocketClient = new ProductionWebSocketClient();
