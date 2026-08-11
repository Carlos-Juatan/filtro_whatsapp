export interface RawMessage {
  id: string;
  timestamp?: string;
  sender?: string;
  content: string;
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

export interface ExtractionProgressLog {
  type: 'log' | 'progress' | 'result' | 'error';
  message?: string;
  stage?: string;
  percent?: number;
  result?: ExtractionResult;
  error?: string;
}
