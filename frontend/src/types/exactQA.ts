export interface RawMessage {
  id: string;
  timestamp?: string;
  sender?: string;
  content: string;
  is_placeholder?: boolean;
}

export interface LLMQAPairMapping {
  question_id: string;
  answer_id: string;
}

export interface ExactQAPair {
  id: string;
  question_id: string;
  question_text: string;
  answer_id: string;
  answer_text: string;
  metadata: {
    question_sender?: string;
    question_timestamp?: string;
    answer_sender?: string;
    answer_timestamp?: string;
    [key: string]: any;
  };
}

export interface ExtractionResult {
  filename: string;
  total_messages_parsed: number;
  total_pairs_extracted: number;
  pairs: ExactQAPair[];
}

/** Progress payload emitted by the backend for each chunk processed (T010) */
export interface ChunkProgressPayload {
  chunk_index: number;
  total_chunks: number;
  pairs_found_in_chunk: number;
  total_pairs_so_far: number;
  percent: number;
}

export interface ExtractionProgressLog {
  type: 'log' | 'chunk_progress' | 'complete' | 'error';
  message?: string;
  data?: ChunkProgressPayload | ExtractionResult;
  timestamp?: string;
  error?: string;
}
