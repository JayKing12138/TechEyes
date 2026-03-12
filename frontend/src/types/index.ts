export interface AnalysisRequest {
  query: string;
  focus_companies?: string[];
  analysis_depth?: 'quick' | 'normal' | 'deep';
  include_future_prediction?: boolean;
}

export interface TaskNode {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  description: string;
  startTime?: number;
  endTime?: number;
  agent: string;
  output?: string;
}

export interface AnalysisState {
  session_id?: string;
  status: 'idle' | 'loading' | 'running' | 'analyzing' | 'completed' | 'error';
  progress: number;
  current_step?: string;
  tasks: TaskNode[];
  errors?: string[];
  currentTask?: TaskNode;
  result?: AnalysisResult;
  errorMessage?: string;
}

export interface AnalysisResult {
  summary: string;
  timeline: TimelineEvent[];
  comparisons: ComparisonData[];
  futureOutlook: FutureOutlook;
  sources: Reference[];
  metadata: {
    totalProcessingTime: number;
    agentsInvolved: string[];
    queryCacheHit: boolean;
  };
}

export interface TimelineEvent {
  date: string;
  title: string;
  description: string;
  companies: string[];
  significance: 'low' | 'medium' | 'high';
}

export interface ComparisonData {
  dimension: string;
  dimension_description: string;
  companies: {
    name: string;
    value: string | number;
    score: number;
  }[];
  analysis: string;
}

export interface FutureOutlook {
  scenarios: Scenario[];
  trends: string[];
  recommendations: string[];
}

export interface Scenario {
  name: string;
  probability: number;
  description: string;
  implications: string[];
}

export interface Reference {
  title: string;
  source: string;
  date: string;
  url?: string;
  relevance: number;
}

export interface ConversationItem {
  conversation_id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_message: string;
}

export interface ChatMessage {
  turn_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  meta?: Record<string, any>;
  created_at: string;
}
