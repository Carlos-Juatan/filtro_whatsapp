import type { ExtractionResult, ExactQAPair } from '../types/exactQA';

export function exportExactQAPairsToTxt(result: ExtractionResult): string {
  const header = `========================================================================\n` +
                 `EXTRAÇÃO EXATA DE PERGUNTAS E RESPOSTAS DO WHATSAPP\n` +
                 `Arquivo: ${result.filename}\n` +
                 `Total de Mensagens: ${result.total_messages_parsed}\n` +
                 `Total de Pares Extraídos: ${result.total_pairs_extracted}\n` +
                 `Data da Extração: ${new Date().toLocaleString('pt-BR')}\n` +
                 `========================================================================\n\n`;

  const body = result.pairs.map((pair: ExactQAPair, idx: number) => {
    const qSender = pair.metadata?.question_sender ? ` (${pair.metadata.question_sender})` : '';
    const aSender = pair.metadata?.answer_sender ? ` (${pair.metadata.answer_sender})` : '';
    
    return `--- PAR ${idx + 1} [ID: ${pair.id}] ---\n` +
           `PERGUNTA [${pair.question_id}]${qSender}:\n${pair.question_text}\n\n` +
           `RESPOSTA [${pair.answer_id}]${aSender}:\n${pair.answer_text}\n`;
  }).join('\n========================================================================\n\n');

  return header + body;
}

export function exportExactQAPairsToJson(result: ExtractionResult): string {
  return JSON.stringify(result, null, 2);
}

export function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
