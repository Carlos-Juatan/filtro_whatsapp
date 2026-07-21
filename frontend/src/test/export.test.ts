import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { exportToJson, exportToTxt, exportToUncategorizedTxt } from '../utils/export';
import { ResultadoParPR } from '../services/api';

describe('Export Utils', () => {
  let mockCreateObjectURL: ReturnType<typeof vi.fn>;
  let mockRevokeObjectURL: ReturnType<typeof vi.fn>;
  let mockClick: ReturnType<typeof vi.fn>;
  let mockAppendChild: ReturnType<typeof vi.fn>;
  let mockRemoveChild: ReturnType<typeof vi.fn>;
  
  let originalBlob: typeof Blob;
  let mockBlobConstructor: ReturnType<typeof vi.fn>;
  const originalCreateElement = document.createElement.bind(document);
  
  beforeEach(() => {
    originalBlob = globalThis.Blob;
    mockBlobConstructor = vi.fn().mockImplementation((content, options) => {
      return {
        _content: content,
        type: options?.type,
        size: 0,
        arrayBuffer: async () => new ArrayBuffer(0),
        slice: () => new Blob(),
        stream: () => new ReadableStream(),
        text: async () => content.join('')
      } as any;
    });
    globalThis.Blob = mockBlobConstructor as any;

    mockCreateObjectURL = vi.fn().mockReturnValue('blob:http://localhost/mock-uuid');
    mockRevokeObjectURL = vi.fn();
    mockClick = vi.fn();
    mockAppendChild = vi.fn();
    mockRemoveChild = vi.fn();

    // Mock URL methods
    globalThis.URL.createObjectURL = mockCreateObjectURL as any;
    globalThis.URL.revokeObjectURL = mockRevokeObjectURL as any;

    // Mock DOM elements and methods
    vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      if (tagName === 'a') {
        return {
          href: '',
          download: '',
          click: mockClick,
        } as any;
      }
      return originalCreateElement(tagName);
    });

    vi.spyOn(document.body, 'appendChild').mockImplementation(mockAppendChild as any);
    vi.spyOn(document.body, 'removeChild').mockImplementation(mockRemoveChild as any);
  });

  afterEach(() => {
    globalThis.Blob = originalBlob;
    vi.restoreAllMocks();
  });

  const sampleData: ResultadoParPR[] = [
    {
      perguntaPadronizada: 'Qual o horário de atendimento?',
      respostaConsolidada: 'O horário é das 8h às 18h.',
      frequencia: 1,
      category: 'Geral',
      metadata: 'Atendimento'
    }
  ];

  it('should export to JSON with correct schema', async () => {
    exportToJson(sampleData, 'test.json');

    expect(mockCreateObjectURL).toHaveBeenCalledOnce();
    
    // Check if a Blob was created
    const blobArg = mockCreateObjectURL.mock.calls[0][0] as Blob;
    expect(blobArg).toBeDefined();
    expect(blobArg.type).toBe('application/json');

    // We can extract text from the blob to verify structure
    const promise = (blobArg as any).text().then((text: string) => {
      const parsed = JSON.parse(text);
      expect(parsed).toHaveProperty('qna_pairs');
      expect(parsed.qna_pairs).toHaveLength(1);
      expect(parsed.qna_pairs[0]).toEqual(sampleData[0]);
    });
    await promise;
    
    expect(mockAppendChild).toHaveBeenCalled();
    expect(mockClick).toHaveBeenCalled();
    expect(mockRemoveChild).toHaveBeenCalled();
    expect(mockRevokeObjectURL).toHaveBeenCalled();
  });

  it('should export to TXT with exact FAQ layout', async () => {
    exportToTxt(sampleData, 'test.txt');

    expect(mockCreateObjectURL).toHaveBeenCalledOnce();
    
    const blobArg = mockCreateObjectURL.mock.calls[0][0] as Blob;
    expect(blobArg).toBeDefined();
    expect(blobArg.type).toBe('text/plain');

    const text = await (blobArg as any).text();
    expect(text).toContain('[Atendimento] (Frequência: 1)');
    expect(text).toContain('Q: Qual o horário de atendimento?');
    expect(text).toContain('A: O horário é das 8h às 18h.');
  });

  it('should export uncategorized content correctly', async () => {
    exportToUncategorizedTxt(['Fato 1', 'Fato 2'], 'uncategorized.txt');

    expect(mockCreateObjectURL).toHaveBeenCalledOnce();
    const blobArg = mockCreateObjectURL.mock.calls[0][0] as Blob;
    expect(blobArg.type).toBe('text/plain;charset=utf-8');

    const text = await (blobArg as any).text();
    expect(text).toContain('Fato 1');
    expect(text).toContain('Fato 2');
    expect(text).toContain('----------------------------------------');
  });
});
