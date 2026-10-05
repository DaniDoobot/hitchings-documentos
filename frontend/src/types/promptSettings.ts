export interface PromptSetting {
  id: string;
  key: string;
  content: string;
  created_at: string;
  updated_at: string;
  updated_by_user_id?: string | null;
  updated_by_email?: string | null;
}

export interface PromptSettingUpdate {
  content: string;
}

export interface PromptOptionsGuidelines {
  detail_levels: Record<string, string>;
  output_formats: Record<string, string>;
}

export interface EffectiveInstructionsRequest {
  prompt_id: string;
  detail_level?: string;
  output_format?: string;
  additional_instructions?: string | null;
}

export interface EffectiveInstructionsResponse {
  base_prompt: string;
  type_name: string;
  type_instructions: string;
  detail_level: string;
  detail_modifier: string;
  output_format: string;
  format_modifier: string;
  additional_instructions?: string | null;
  effective_full_prompt: string;
}
