export type DetailLevel = 'brief' | 'standard' | 'detailed';
export type OutputFormat = 'prose' | 'sections' | 'bullet_points';
export type TranscriptionMode = 'verbatim' | 'smart';
export type InputTab = 'document' | 'audio' | 'text';

export type ProcessingStage =
  | 'idle'
  | 'preparing'
  | 'extracting'
  | 'transcribing'
  | 'analyzing'
  | 'completed'
  | 'error';

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
  additional_instructions?: string | null;
}

export interface AnalysisRequest {
  text: string;
  prompt_id: string;
  options: AnalysisOptions;
}

export interface AnalysisUsage {
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
}

export interface AnalysisResponse {
  prompt_id: string;
  prompt_name: string;
  model: string;
  options: AnalysisOptions;
  title: string;
  content: string;
  warnings: string[];
  usage?: AnalysisUsage | null;
}

export interface DocumentExtractResponse {
  filename: string;
  extension: string;
  content_type: string;
  size_bytes: number;
  page_count: number | null;
  word_count: number;
  character_count: number;
  text: string;
  warnings: string[];
}

export interface SpeakerSegment {
  speaker: string;
  text: string;
}

export interface AudioTranscriptionUsage {
  input_tokens?: number | null;
  output_tokens?: number | null;
  total_tokens?: number | null;
}

export interface AudioTranscribeResponse {
  filename: string;
  extension: string;
  content_type: string;
  size_bytes: number;
  transcription_model: string;
  mode: string;
  diarization: boolean;
  text: string;
  word_count: number;
  character_count: number;
  detected_language?: string | null;
  language?: string | null;
  segments: SpeakerSegment[];
  warnings: string[];
  usage?: AudioTranscriptionUsage | null;
}

export interface TextPrepareRequest {
  text: string;
}

export interface TextPrepareResponse {
  text: string;
  word_count: number;
  character_count: number;
}

export interface WordExportMetadata {
  prompt_name?: string | null;
  model?: string | null;
}

export interface WordExportRequest {
  title: string;
  content: string;
  warnings: string[];
  metadata?: WordExportMetadata | null;
}

export interface WordExportResult {
  blob: Blob;
  filename: string;
}

