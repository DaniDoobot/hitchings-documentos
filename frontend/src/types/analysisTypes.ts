export interface AnalysisType {
  id: string;
  code: string;
  name: string;
  description: string;
  instructions: string;
  is_active: boolean;
  created_by_user_id: string | null;
  updated_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisTypeListResponse {
  items: AnalysisType[];
  total: number;
}


export interface AnalysisTypeCreatePayload {
  name: string;
  description: string;
  instructions: string;
  is_active: boolean;
}

export interface AnalysisTypeUpdatePayload {
  name?: string;
  description?: string;
  instructions?: string;
  is_active?: boolean;
}
