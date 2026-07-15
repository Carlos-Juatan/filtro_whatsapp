import { ResultadoParPR } from "../services/api";

export function exportToJson(data: ResultadoParPR[], filename = "resultados.json") {
  const validData = data.filter(
    (item) =>
      item.perguntaPadronizada &&
      item.respostaConsolidada &&
      typeof item.frequencia === "number" &&
      item.category
  );
  const blob = new Blob([JSON.stringify({ qna_pairs: validData }, null, 2)], { type: "application/json" });
  triggerDownload(blob, filename);
}

export function exportToTxt(data: ResultadoParPR[], filename = "resultados.txt") {
  const lines = data.map(
    (item) =>
      `[${item.metadata || item.category}] (Frequência: ${item.frequencia})\n` +
      `Q: ${item.perguntaPadronizada}\n` +
      `A: ${item.respostaConsolidada}\n` +
      `----------------------------------------`
  );
  const blob = new Blob([lines.join("\n\n")], { type: "text/plain" });
  triggerDownload(blob, filename);
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Export the deduplicated uncategorized content statements as a plain .txt file.
 * Each statement is on its own line, separated by \n, with no markers or prefixes.
 * (FR-006, SC-002, SC-003)
 */
export function exportToUncategorizedTxt(
  items: string[],
  filename = "nao_classificados.txt"
) {
  const content = `\n${items.join("\n\n----------------------------------------\n\n")}\n`;
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  triggerDownload(blob, filename);
}
