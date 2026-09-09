export type DetailLevel = 'brief' | 'standard' | 'detailed';
export type OutputFormat = 'prose' | 'sections' | 'bullet_points';
export type TranscriptionMode = 'verbatim' | 'smart';
export type InputTab = 'document' | 'audio' | 'text';

export interface Prompt {
  id: string;
  name: string;
  description: string;
  instructions: string;
  is_active: boolean;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface PromptListResponse {
  prompts: Prompt[];
  total: number;
}

export interface AnalysisOptions {
  detail_level: DetailLevel;
  output_format: OutputFormat;
  additional_instructions: string;
}

export interface AudioTranscriptionOptions {
  mode: TranscriptionMode;
  diarization: boolean;
}

export interface DocumentExtractResponse {
  filename: string;
  text: string;
  character_count: number;
  word_count: number;
  warnings: string[];
}

export interface AudioTranscriptionResponse {
  transcript: string;
  mode: TranscriptionMode;
  diarization: boolean;
  character_count: number;
  word_count: number;
  duration_seconds?: number;
  model: string;
}

export interface AnalysisResponse {
  summary: string;
  full_text: string;
  key_points: string[];
  warnings: string[];
  metadata: {
    model?: string;
    prompt_name?: string;
    tokens_used?: number;
    processing_time_ms?: number;
    [key: string]: unknown;
  };
}

export interface WordExportRequest {
  title: string;
  content: string;
  warnings?: string[];
  metadata?: {
    prompt_name?: string;
    model?: string;
  };
}
