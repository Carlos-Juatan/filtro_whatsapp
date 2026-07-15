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
