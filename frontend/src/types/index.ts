export type UserRole = 'CITIZEN' | 'OFFICER' | 'DISTRICT_ADMIN' | 'SUPER_ADMIN';

export interface User {
  id: string;
  email: string;
  full_name: string;
  mobile?: string;
  role: UserRole;
  district_code?: string;
  department_id?: string;
}

export type ComplaintStatus =
  | 'SUBMITTED'
  | 'RECEIVED'
  | 'ASSIGNED'
  | 'IN_PROGRESS'
  | 'ON_HOLD'
  | 'RESOLVED'
  | 'CLOSED'
  | 'REJECTED'
  | 'REOPENED';

export type Priority = 'LOW' | 'MEDIUM' | 'HIGH';

export interface District {
  code: string;
  name: string;
  name_en?: string;
  name_hi?: string;
}

export interface Department {
  id: string;
  code: string;
  name_en: string;
  name_hi?: string;
}

export interface CategoryMapping {
  department_id: string;
  department?: Department;
}

export interface Category {
  id: string;
  name_en: string;
  name_hi?: string;
  description?: string;
  default_priority?: Priority;
  sla_days?: number;
  mappings?: CategoryMapping[];
}

export interface Attachment {
  id: string;
  file_name: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  uploaded_at: string;
}

export interface StatusHistoryItem {
  id: string;
  old_status?: ComplaintStatus;
  new_status: ComplaintStatus;
  actor_role: string;
  remarks?: string;
  timestamp: string;
}

export interface ComplaintMessage {
  id: string;
  sender_role: string;
  message: string;
  created_at: string;
}

export interface ComplaintFeedback {
  id: string;
  rating: number;
  comments?: string;
  is_satisfied: boolean;
  created_at?: string;
}

export interface Complaint {
  id: string;
  complaint_no: string;
  tracking_code?: string;
  is_anonymous: boolean;
  subject: string;
  description: string;
  district_code: string;
  category_id: string;
  category?: Category;
  department_id?: string;
  department?: Department;
  priority: Priority;
  status: ComplaintStatus;
  location_address: string;
  contact_email?: string;
  contact_mobile?: string;
  assigned_officer_id?: string;
  assigned_officer_name?: string;
  sla_deadline: string;
  is_overdue?: boolean;
  resolution_summary?: string;
  resolved_at?: string;
  created_at: string;
  updated_at: string;
  attachments?: Attachment[];
  status_history?: StatusHistoryItem[];
  messages?: ComplaintMessage[];
  feedback?: ComplaintFeedback;
}

export interface AIRecommendation {
  suggested_category_id?: string;
  suggested_category_name?: string;
  suggested_priority?: Priority;
  confidence: number;
  reasoning: string;
  provider: string;
}

export interface PublicAnalytics {
  total_complaints: number;
  resolved_complaints: number;
  in_progress_complaints: number;
  resolution_rate_percent: number;
  category_trends?: Array<{ name_en: string; count: number }>;
}

export interface Officer {
  id: string;
  user_id: string;
  officer_id: string;
  full_name: string;
  email: string;
  department_id: string;
  department?: Department;
  district_code: string;
  active_workload: number;
  is_available: boolean;
}

export interface ReopenRequest {
  id: string;
  complaint_id: string;
  justification: string;
  created_at: string;
  complaint?: {
    complaint_no: string;
    subject: string;
    status: ComplaintStatus;
  };
}

export interface AIInsights {
  summary_text: string;
  highlights?: string[];
  operational_suggestions?: string[];
}
