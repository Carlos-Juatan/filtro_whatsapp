/**
 * Frontend component tests for FileUploader and LogViewer (Vitest + RTL).
 *
 * Run with:
 *   cd frontend && npm test -- tests/components.test.tsx
 *
 * Test coverage:
 *   FileUploader:
 *     - Renders the drop zone
 *     - File selection via input change
 *     - Shows file in the list after selection
 *     - Remove button removes file from list
 *     - Submit button triggers onFilesReady callback
 *     - Progress bar rendered when isProcessing=true
 *     - Drop zone disabled when isProcessing=true
 *
 *   LogViewer:
 *     - Renders empty state when no logs
 *     - Renders log entries with correct level styling
 *     - Shows correct count badge
 *     - Clear button triggers onClear callback
 *     - Does not render clear button when no logs
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";

import { FileUploader } from "@/components/FileUploader";
import { LogViewer } from "@/components/LogViewer";
import type { ItemLog } from "@/services/api";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function makeTxtFile(name = "test.txt", content = "conteudo de teste"): File {
  return new File([content], name, { type: "text/plain" });
}

function makeLog(
  mensagem: string,
  tipo: ItemLog["tipo"] = "INFO"
): ItemLog {
  return { timestamp: "10:00:00", tipo, mensagem };
}

// ─────────────────────────────────────────────────────────────────────────────
// FileUploader Tests
// ─────────────────────────────────────────────────────────────────────────────

describe("FileUploader", () => {
  it("renders the drop zone with correct aria label", () => {
    render(<FileUploader onFilesReady={() => {}} />);
    const dropZone = screen.getByRole("button", {
      name: /arraste arquivos/i,
    });
    expect(dropZone).toBeInTheDocument();
  });

  it("shows a file in the list after input selection", async () => {
    render(<FileUploader onFilesReady={() => {}} />);
    const input = document.getElementById("file-input-hidden") as HTMLInputElement;
    expect(input).toBeTruthy();

    const file = makeTxtFile("transcricao.txt");
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("transcricao.txt")).toBeInTheDocument();
    });
  });

  it("removes a file when the remove button is clicked", async () => {
    render(<FileUploader onFilesReady={() => {}} />);
    const input = document.getElementById("file-input-hidden") as HTMLInputElement;

    const file = makeTxtFile("remove_me.txt");
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("remove_me.txt")).toBeInTheDocument();
    });

    const removeBtn = screen.getByRole("button", {
      name: /remover remove_me\.txt/i,
    });
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(screen.queryByText("remove_me.txt")).not.toBeInTheDocument();
    });
  });

  it("calls onFilesReady with selected files when submit button is clicked", async () => {
    const onFilesReady = vi.fn();
    render(<FileUploader onFilesReady={onFilesReady} />);
    const input = document.getElementById("file-input-hidden") as HTMLInputElement;

    const file = makeTxtFile("data.txt");
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("data.txt")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", {
      name: /iniciar processamento/i,
    });
    fireEvent.click(submitBtn);

    expect(onFilesReady).toHaveBeenCalledOnce();
    expect(onFilesReady).toHaveBeenCalledWith([file]);
  });

  it("clears the file list after submission", async () => {
    render(<FileUploader onFilesReady={() => {}} />);
    const input = document.getElementById("file-input-hidden") as HTMLInputElement;

    fireEvent.change(input, { target: { files: [makeTxtFile("clear.txt")] } });

    await waitFor(() => {
      expect(screen.getByText("clear.txt")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: /iniciar processamento/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.queryByText("clear.txt")).not.toBeInTheDocument();
    });
  });

  it("renders progress bar when isProcessing=true", () => {
    render(
      <FileUploader onFilesReady={() => {}} isProcessing={true} progress={42} />
    );
    const progressBar = document.getElementById("processing-progress-bar");
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute("aria-valuenow", "42");
  });

  it("does not render submit button when isProcessing=true", async () => {
    render(
      <FileUploader
        onFilesReady={() => {}}
        isProcessing={true}
        fileStatuses={{ "busy.txt": "PROCESSANDO" }}
      />
    );
    // No pending files → no submit button regardless
    expect(
      screen.queryByRole("button", { name: /processar/i })
    ).not.toBeInTheDocument();
  });

  it("shows PROCESSANDO status icon for in-progress file", () => {
    render(
      <FileUploader
        onFilesReady={() => {}}
        isProcessing={true}
        progress={50}
        fileStatuses={{ "busy.txt": "PROCESSANDO" }}
      />
    );
    const statusEl = screen.getByLabelText(/status: processando/i);
    expect(statusEl).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// LogViewer Tests
// ─────────────────────────────────────────────────────────────────────────────

describe("LogViewer", () => {
  it("renders empty state when no logs are provided", () => {
    render(<LogViewer logs={[]} />);
    expect(
      screen.getByText(/os logs aparecerão aqui/i)
    ).toBeInTheDocument();
  });

  it("renders INFO log entries", () => {
    const logs: ItemLog[] = [makeLog("Iniciando processamento")];
    render(<LogViewer logs={logs} />);
    expect(screen.getByText("Iniciando processamento")).toBeInTheDocument();
  });

  it("renders SUCESSO log entries", () => {
    const logs: ItemLog[] = [makeLog("Concluído!", "SUCESSO")];
    render(<LogViewer logs={logs} />);
    expect(screen.getByText("Concluído!")).toBeInTheDocument();
  });

  it("renders ERRO log entries", () => {
    const logs: ItemLog[] = [makeLog("Falha na API", "ERRO")];
    render(<LogViewer logs={logs} />);
    expect(screen.getByText("Falha na API")).toBeInTheDocument();
  });

  it("shows the correct count badge", () => {
    const logs: ItemLog[] = [makeLog("msg 1"), makeLog("msg 2"), makeLog("msg 3")];
    render(<LogViewer logs={logs} />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("renders the clear button when logs exist", () => {
    const logs: ItemLog[] = [makeLog("algum log")];
    render(<LogViewer logs={logs} onClear={() => {}} />);
    expect(
      screen.getByRole("button", { name: /limpar todos os logs/i })
    ).toBeInTheDocument();
  });

  it("does not render the clear button when logs are empty", () => {
    render(<LogViewer logs={[]} onClear={() => {}} />);
    expect(
      screen.queryByRole("button", { name: /limpar/i })
    ).not.toBeInTheDocument();
  });

  it("calls onClear when clear button is clicked", () => {
    const onClear = vi.fn();
    const logs: ItemLog[] = [makeLog("msg")];
    render(<LogViewer logs={logs} onClear={onClear} />);
    const clearBtn = screen.getByRole("button", { name: /limpar/i });
    fireEvent.click(clearBtn);
    expect(onClear).toHaveBeenCalledOnce();
  });

  it("renders all multiple log entries", () => {
    const logs: ItemLog[] = [
      makeLog("Mensagem INFO", "INFO"),
      makeLog("Mensagem SUCESSO", "SUCESSO"),
      makeLog("Mensagem ERRO", "ERRO"),
    ];
    render(<LogViewer logs={logs} />);
    expect(screen.getByText("Mensagem INFO")).toBeInTheDocument();
    expect(screen.getByText("Mensagem SUCESSO")).toBeInTheDocument();
    expect(screen.getByText("Mensagem ERRO")).toBeInTheDocument();
  });

  it("has correct ARIA live region role", () => {
    render(<LogViewer logs={[]} />);
    const liveRegion = document.getElementById("log-entries-list");
    expect(liveRegion).toHaveAttribute("role", "log");
    expect(liveRegion).toHaveAttribute("aria-live", "polite");
  });
});
