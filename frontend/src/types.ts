export type UserRole = "PROVIDER" | "INFUSION_ADMIN";
export type OrgType = "PROVIDER_ORG" | "INFUSION_ORG";

export type CaseStatus =
  | "REFERRAL_RECEIVED"
  | "CLINICAL_COMPLETENESS_CHECK"
  | "BENEFITS_INVESTIGATION"
  | "PRIOR_AUTH_SUBMITTED"
  | "PRIOR_AUTH_APPROVED"
  | "FINANCIAL_COUNSELING_PENDING"
  | "FINANCIAL_CLEARED"
  | "WELCOME_CALL_PENDING"
  | "WELCOME_CALL_COMPLETED"
  | "SCHEDULING_READY"
  | "SCHEDULED"
  | "PHARMACY_PUSH_PENDING"
  | "PHARMACY_PUSHED"
  | "DRUG_FULFILLMENT_IN_PROGRESS"
  | "DRUG_READY"
  | "INFUSION_COMPLETED"
  | "ON_THERAPY"
  | "DISCONTINUED";

export type TaskType =
  | "CLINICAL_REVIEW"
  | "BENEFITS_INVESTIGATION"
  | "PRIOR_AUTH"
  | "FINANCIAL_COUNSELING"
  | "WELCOME_CALL"
  | "SCHEDULING"
  | "PHARMACY_PUSH"
  | "DOCUMENT_REQUEST"
  | "GENERAL";

export type TaskStatus = "PENDING" | "IN_PROGRESS" | "DONE" | "CANCELLED";

export type FulfillmentStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "READY"
  | "SHIPPED"
  | "RECEIVED";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  org_id: string;
}

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  dob?: string;
  phone?: string;
  email?: string;
}

export interface Prescription {
  id: string;
  case_id: string;
  drug_name?: string;
  dose?: string;
  frequency?: string;
  route?: string;
  diagnosis_icd10?: string;
}

export interface Insurance {
  id: string;
  case_id: string;
  payer_name?: string;
  member_id?: string;
  group_id?: string;
}

export interface CaseSummary {
  id: string;
  status: CaseStatus;
  provider_org_id: string;
  infusion_org_id?: string;
  created_by_user_id: string;
  created_at: string;
  updated_at?: string;
  patient?: Patient;
}

export interface CaseDetail extends CaseSummary {
  prescription?: Prescription;
  insurance?: Insurance;
}

export interface Task {
  id: string;
  case_id: string;
  type: TaskType;
  status: TaskStatus;
  owner_user_id?: string;
  due_at?: string;
  payload_json?: Record<string, unknown>;
  created_at: string;
  updated_at?: string;
}

export interface TimelineEvent {
  id: string;
  case_id: string;
  event_type: string;
  actor_user_id?: string;
  metadata_json?: Record<string, unknown>;
  created_at: string;
}

export interface Schedule {
  id: string;
  case_id: string;
  date_time: string;
  location?: string;
  duration_minutes?: number;
}

export interface FinancialClearance {
  id: string;
  case_id: string;
  benefits_verified_at?: string;
  cost_estimate_amount?: number;
  patient_acknowledged_cost: boolean;
  assistance_program?: string;
  cleared_at?: string;
}

export interface PharmacyOrder {
  id: string;
  case_id: string;
  pushed_at?: string;
  ship_to?: string;
  requested_arrival_date?: string;
  fulfillment_status: FulfillmentStatus;
  pharmacy_notes?: string;
  ndc?: string;
  lot?: string;
  expiration_date?: string;
}

export interface Document {
  id: string;
  case_id: string;
  file_name: string;
  file_type?: string;
  storage_url?: string;
  uploaded_by_user_id: string;
  created_at: string;
}

export interface Blocker {
  type: string;
  message: string;
  fields?: string[];
}

export const STATUS_LABELS: Record<CaseStatus, string> = {
  REFERRAL_RECEIVED: "Referral Received",
  CLINICAL_COMPLETENESS_CHECK: "Clinical Completeness Check",
  BENEFITS_INVESTIGATION: "Benefits Investigation",
  PRIOR_AUTH_SUBMITTED: "Prior Auth Submitted",
  PRIOR_AUTH_APPROVED: "Prior Auth Approved",
  FINANCIAL_COUNSELING_PENDING: "Financial Counseling Pending",
  FINANCIAL_CLEARED: "Financial Cleared",
  WELCOME_CALL_PENDING: "Welcome Call Pending",
  WELCOME_CALL_COMPLETED: "Welcome Call Completed",
  SCHEDULING_READY: "Scheduling Ready",
  SCHEDULED: "Scheduled",
  PHARMACY_PUSH_PENDING: "Pharmacy Push Pending",
  PHARMACY_PUSHED: "Pharmacy Pushed",
  DRUG_FULFILLMENT_IN_PROGRESS: "Drug Fulfillment In Progress",
  DRUG_READY: "Drug Ready",
  INFUSION_COMPLETED: "Infusion Completed",
  ON_THERAPY: "On Therapy",
  DISCONTINUED: "Discontinued",
};

export const STATUS_COLORS: Record<CaseStatus, string> = {
  REFERRAL_RECEIVED: "#6366f1",
  CLINICAL_COMPLETENESS_CHECK: "#8b5cf6",
  BENEFITS_INVESTIGATION: "#a78bfa",
  PRIOR_AUTH_SUBMITTED: "#f59e0b",
  PRIOR_AUTH_APPROVED: "#10b981",
  FINANCIAL_COUNSELING_PENDING: "#f97316",
  FINANCIAL_CLEARED: "#10b981",
  WELCOME_CALL_PENDING: "#f97316",
  WELCOME_CALL_COMPLETED: "#10b981",
  SCHEDULING_READY: "#3b82f6",
  SCHEDULED: "#10b981",
  PHARMACY_PUSH_PENDING: "#f97316",
  PHARMACY_PUSHED: "#3b82f6",
  DRUG_FULFILLMENT_IN_PROGRESS: "#f59e0b",
  DRUG_READY: "#10b981",
  INFUSION_COMPLETED: "#10b981",
  ON_THERAPY: "#059669",
  DISCONTINUED: "#ef4444",
};
