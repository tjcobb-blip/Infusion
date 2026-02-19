import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../AuthContext";
import type {
  CaseDetail,
  Task as TaskType,
  TimelineEvent,
  Schedule,
  FinancialClearance,
  PharmacyOrder,
  Blocker,
  Document,
  CaseStatus,
  TaskStatus,
} from "../types";
import { STATUS_LABELS, STATUS_COLORS } from "../types";

const NEXT_STATUS_MAP: Partial<Record<CaseStatus, CaseStatus>> = {
  REFERRAL_RECEIVED: "CLINICAL_COMPLETENESS_CHECK",
  CLINICAL_COMPLETENESS_CHECK: "BENEFITS_INVESTIGATION",
  BENEFITS_INVESTIGATION: "PRIOR_AUTH_SUBMITTED",
  PRIOR_AUTH_SUBMITTED: "PRIOR_AUTH_APPROVED",
  PRIOR_AUTH_APPROVED: "FINANCIAL_COUNSELING_PENDING",
  FINANCIAL_COUNSELING_PENDING: "FINANCIAL_CLEARED",
  FINANCIAL_CLEARED: "WELCOME_CALL_PENDING",
  WELCOME_CALL_PENDING: "WELCOME_CALL_COMPLETED",
  WELCOME_CALL_COMPLETED: "SCHEDULING_READY",
  SCHEDULING_READY: "SCHEDULED",
  SCHEDULED: "PHARMACY_PUSH_PENDING",
  PHARMACY_PUSH_PENDING: "PHARMACY_PUSHED",
  PHARMACY_PUSHED: "DRUG_FULFILLMENT_IN_PROGRESS",
  DRUG_FULFILLMENT_IN_PROGRESS: "DRUG_READY",
  DRUG_READY: "INFUSION_COMPLETED",
  INFUSION_COMPLETED: "ON_THERAPY",
};

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "INFUSION_ADMIN";

  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [tasks, setTasks] = useState<TaskType[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [financial, setFinancial] = useState<FinancialClearance | null>(null);
  const [pharmacy, setPharmacy] = useState<PharmacyOrder | null>(null);
  const [blockers, setBlockers] = useState<Blocker[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activeTab, setActiveTab] = useState("overview");
  const [error, setError] = useState("");
  const [statusError, setStatusError] = useState("");

  const loadAll = useCallback(async () => {
    if (!id) return;
    try {
      const [cRes, tRes, tlRes, sRes, fRes, pRes, bRes, dRes] =
        await Promise.all([
          api.get(`/cases/${id}`),
          api.get(`/cases/${id}/tasks`),
          api.get(`/cases/${id}/timeline`),
          api.get(`/cases/${id}/schedule`),
          api.get(`/cases/${id}/financial`),
          api.get(`/cases/${id}/pharmacy-push`),
          api.get(`/cases/${id}/blockers`),
          api.get(`/cases/${id}/documents`),
        ]);
      setCaseData(cRes.data);
      setTasks(tRes.data);
      setTimeline(tlRes.data);
      setSchedule(sRes.data);
      setFinancial(fRes.data);
      setPharmacy(pRes.data);
      setBlockers(bRes.data);
      setDocuments(dRes.data);
    } catch {
      setError("Failed to load case.");
    }
  }, [id]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const advanceStatus = async (newStatus: CaseStatus) => {
    setStatusError("");
    try {
      await api.patch(`/cases/${id}/status`, { new_status: newStatus });
      await loadAll();
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      setStatusError(detail || "Transition failed.");
    }
  };

  if (error) {
    return (
      <div className="page">
        <div className="error-message">{error}</div>
      </div>
    );
  }
  if (!caseData) {
    return <div className="page">Loading...</div>;
  }

  const nextStatus = NEXT_STATUS_MAP[caseData.status];
  const timeInStatus = caseData.updated_at
    ? Math.floor(
        (Date.now() - new Date(caseData.updated_at).getTime()) / 3600000
      )
    : 0;
  const slaClass =
    timeInStatus > 72 ? "danger" : timeInStatus > 24 ? "warning" : "";

  const adminTabs = [
    "overview",
    "financial",
    "welcome-call",
    "scheduling",
    "pharmacy",
    "tasks",
    "documents",
    "timeline",
  ];
  const providerTabs = ["overview", "documents", "timeline"];
  const tabs = isAdmin ? adminTabs : providerTabs;

  return (
    <div className="page">
      <div style={{ marginBottom: 16 }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate("/cases")}>
          &larr; Back to Cases
        </button>
      </div>

      <div className="case-detail-grid">
        <div>
          {/* Header */}
          <div className="card">
            <div className="flex-between">
              <div>
                <h1 style={{ fontSize: 20, fontWeight: 700 }}>
                  {caseData.patient
                    ? `${caseData.patient.first_name} ${caseData.patient.last_name}`
                    : "No Patient"}
                </h1>
                <span className="text-muted">Case {caseData.id.slice(0, 8)}...</span>
              </div>
              <div style={{ textAlign: "right" }}>
                <span
                  className="status-badge"
                  style={{ background: STATUS_COLORS[caseData.status], fontSize: 14 }}
                >
                  {STATUS_LABELS[caseData.status]}
                </span>
                <div className={`sla-timer ${slaClass}`} style={{ marginTop: 4 }}>
                  {timeInStatus}h in current status
                </div>
              </div>
            </div>

            {/* Claim / Assign for unassigned cases */}
            {isAdmin && !caseData.infusion_org_id && (
              <ClaimCaseBar caseId={id!} userOrgId={user!.org_id} onClaimed={loadAll} />
            )}

            {isAdmin && nextStatus && (
              <div style={{ marginTop: 12 }}>
                <button
                  className="btn btn-primary"
                  onClick={() => advanceStatus(nextStatus)}
                >
                  Advance to {STATUS_LABELS[nextStatus]}
                </button>
                {caseData.status !== "DISCONTINUED" && (
                  <button
                    className="btn btn-danger"
                    style={{ marginLeft: 8 }}
                    onClick={() => advanceStatus("DISCONTINUED")}
                  >
                    Discontinue
                  </button>
                )}
                {statusError && (
                  <div className="error-message" style={{ marginTop: 8 }}>
                    {statusError}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Tabs */}
          <div className="tabs">
            {tabs.map((t) => (
              <button
                key={t}
                className={`tab ${activeTab === t ? "active" : ""}`}
                onClick={() => setActiveTab(t)}
              >
                {t.charAt(0).toUpperCase() + t.slice(1).replace("-", " ")}
              </button>
            ))}
          </div>

          {/* Tab content */}
          {activeTab === "overview" && (
            <OverviewTab caseData={caseData} />
          )}
          {activeTab === "financial" && isAdmin && (
            <FinancialTab caseId={id!} financial={financial} onUpdate={loadAll} />
          )}
          {activeTab === "welcome-call" && isAdmin && (
            <WelcomeCallTab caseId={id!} tasks={tasks} onUpdate={loadAll} />
          )}
          {activeTab === "scheduling" && isAdmin && (
            <SchedulingTab caseId={id!} schedule={schedule} onUpdate={loadAll} />
          )}
          {activeTab === "pharmacy" && isAdmin && (
            <PharmacyTab caseId={id!} pharmacy={pharmacy} onUpdate={loadAll} />
          )}
          {activeTab === "tasks" && isAdmin && (
            <TasksTab caseId={id!} tasks={tasks} onUpdate={loadAll} />
          )}
          {activeTab === "documents" && (
            <DocumentsTab caseId={id!} documents={documents} onUpdate={loadAll} />
          )}
          {activeTab === "timeline" && <TimelineTab timeline={timeline} />}
        </div>

        {/* Sidebar */}
        <div className="case-sidebar">
          <div className="card">
            <div className="card-title" style={{ marginBottom: 12 }}>
              Blockers
            </div>
            {blockers.length === 0 ? (
              <div className="text-muted">No blockers - ready to advance!</div>
            ) : (
              blockers.map((b, i) => (
                <div key={i} className="blocker-item">
                  <span className="blocker-icon">!</span>
                  <span>{b.message}</span>
                </div>
              ))
            )}
          </div>

          <div className="card">
            <div className="card-title" style={{ marginBottom: 12 }}>
              Recent Activity
            </div>
            <div className="timeline">
              {timeline.slice(0, 5).map((e) => (
                <div key={e.id} className="timeline-item">
                  <div className="timeline-dot" />
                  <div className="timeline-content">
                    <div className="timeline-event-type">
                      {e.event_type.replace(/_/g, " ")}
                    </div>
                    <div className="timeline-time">
                      {new Date(e.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Overview Tab ────────────────────────────────────────────────────── */
function OverviewTab({ caseData }: { caseData: CaseDetail }) {
  return (
    <>
      <div className="card">
        <div className="card-title">Patient Information</div>
        {caseData.patient ? (
          <div className="grid-2" style={{ marginTop: 12 }}>
            <div>
              <div className="text-muted">Name</div>
              <div>{caseData.patient.first_name} {caseData.patient.last_name}</div>
            </div>
            <div>
              <div className="text-muted">Date of Birth</div>
              <div>{caseData.patient.dob || "N/A"}</div>
            </div>
            <div>
              <div className="text-muted">Phone</div>
              <div>{caseData.patient.phone || "N/A"}</div>
            </div>
            <div>
              <div className="text-muted">Email</div>
              <div>{caseData.patient.email || "N/A"}</div>
            </div>
          </div>
        ) : (
          <div className="text-muted mt-2">No patient attached.</div>
        )}
      </div>

      <div className="card">
        <div className="card-title">Prescription</div>
        {caseData.prescription ? (
          <div className="grid-2" style={{ marginTop: 12 }}>
            <div>
              <div className="text-muted">Drug</div>
              <div>{caseData.prescription.drug_name || "N/A"}</div>
            </div>
            <div>
              <div className="text-muted">Dose</div>
              <div>{caseData.prescription.dose || "N/A"}</div>
            </div>
            <div>
              <div className="text-muted">Frequency</div>
              <div>{caseData.prescription.frequency || "N/A"}</div>
            </div>
            <div>
              <div className="text-muted">Route</div>
              <div>{caseData.prescription.route || "N/A"}</div>
            </div>
            <div>
              <div className="text-muted">Diagnosis (ICD-10)</div>
              <div>{caseData.prescription.diagnosis_icd10 || "N/A"}</div>
            </div>
          </div>
        ) : (
          <div className="text-muted mt-2">No prescription.</div>
        )}
      </div>

      <div className="card">
        <div className="card-title">Insurance</div>
        {caseData.insurance ? (
          <div className="grid-2" style={{ marginTop: 12 }}>
            <div>
              <div className="text-muted">Payer</div>
              <div>{caseData.insurance.payer_name || "N/A"}</div>
            </div>
            <div>
              <div className="text-muted">Member ID</div>
              <div>{caseData.insurance.member_id || "N/A"}</div>
            </div>
            <div>
              <div className="text-muted">Group ID</div>
              <div>{caseData.insurance.group_id || "N/A"}</div>
            </div>
          </div>
        ) : (
          <div className="text-muted mt-2">No insurance info.</div>
        )}
      </div>
    </>
  );
}

/* ── Financial Tab ───────────────────────────────────────────────────── */
function FinancialTab({
  caseId,
  financial,
  onUpdate,
}: {
  caseId: string;
  financial: FinancialClearance | null;
  onUpdate: () => void;
}) {
  const [costEstimate, setCostEstimate] = useState(
    financial?.cost_estimate_amount?.toString() || ""
  );
  const [acknowledged, setAcknowledged] = useState(
    financial?.patient_acknowledged_cost || false
  );
  const [assistance, setAssistance] = useState(
    financial?.assistance_program || ""
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const save = async (markCleared: boolean) => {
    setSaving(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {
        cost_estimate_amount: costEstimate ? parseFloat(costEstimate) : undefined,
        patient_acknowledged_cost: acknowledged,
        assistance_program: assistance || undefined,
      };
      if (!financial?.benefits_verified_at) {
        payload.benefits_verified_at = new Date().toISOString();
      }
      if (markCleared) {
        payload.cleared_at = new Date().toISOString();
        payload.patient_acknowledged_cost = true;
      }
      await api.patch(`/cases/${caseId}/financial`, payload);
      onUpdate();
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      setError(detail || "Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <div className="card-title">Financial Counseling</div>
      {error && <div className="error-message mt-2">{error}</div>}

      {financial?.cleared_at ? (
        <div
          style={{
            marginTop: 12,
            padding: 12,
            background: "#ecfdf5",
            borderRadius: 6,
            color: "#059669",
            fontWeight: 600,
          }}
        >
          Financial Cleared on{" "}
          {new Date(financial.cleared_at).toLocaleDateString()}
        </div>
      ) : null}

      <div style={{ marginTop: 16 }}>
        <div className="grid-2">
          <div className="form-group">
            <label>Cost Estimate ($)</label>
            <input
              className="form-control"
              type="number"
              value={costEstimate}
              onChange={(e) => setCostEstimate(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Assistance Program</label>
            <input
              className="form-control"
              value={assistance}
              onChange={(e) => setAssistance(e.target.value)}
            />
          </div>
        </div>

        <div className="checklist-item">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
          />
          <span>Patient acknowledged cost</span>
        </div>

        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button
            className="btn btn-secondary"
            onClick={() => save(false)}
            disabled={saving}
          >
            Save Progress
          </button>
          <button
            className="btn btn-success"
            onClick={() => save(true)}
            disabled={saving || !acknowledged}
          >
            Mark Cleared
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Welcome Call Tab ────────────────────────────────────────────────── */
function WelcomeCallTab({
  caseId,
  tasks,
  onUpdate,
}: {
  caseId: string;
  tasks: TaskType[];
  onUpdate: () => void;
}) {
  const wcTask = tasks.find((t) => t.type === "WELCOME_CALL");
  const payload = (wcTask?.payload_json || {}) as Record<string, unknown>;

  const [reached, setReached] = useState((payload.reached as boolean) || false);
  const [outcome, setOutcome] = useState(
    (payload.outcome as string) || "REACHED"
  );
  const [questions, setQuestions] = useState(
    (payload.patient_questions as string) || ""
  );
  const [nextSteps, setNextSteps] = useState(
    (payload.next_steps as string) || ""
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const save = async (markDone: boolean) => {
    setSaving(true);
    setError("");
    try {
      const newPayload = {
        reached,
        outcome,
        patient_questions: questions,
        next_steps: nextSteps,
      };

      if (wcTask) {
        const update: Record<string, unknown> = { payload_json: newPayload };
        if (markDone) update.status = "DONE";
        await api.patch(`/tasks/${wcTask.id}`, update);
      } else {
        await api.post(`/cases/${caseId}/tasks`, {
          type: "WELCOME_CALL",
          payload_json: newPayload,
          status: markDone ? "DONE" : "IN_PROGRESS",
        });
      }
      onUpdate();
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      setError(detail || "Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  const isDone = wcTask?.status === "DONE";

  return (
    <div className="card">
      <div className="card-title">Welcome Call</div>
      {error && <div className="error-message mt-2">{error}</div>}

      {isDone && (
        <div
          style={{
            marginTop: 12,
            padding: 12,
            background: "#ecfdf5",
            borderRadius: 6,
            color: "#059669",
            fontWeight: 600,
          }}
        >
          Welcome call completed
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <div className="checklist-item">
          <input
            type="checkbox"
            checked={reached}
            onChange={(e) => setReached(e.target.checked)}
          />
          <span>Patient reached</span>
        </div>

        <div className="form-group">
          <label>Call Outcome</label>
          <select
            className="form-control"
            value={outcome}
            onChange={(e) => setOutcome(e.target.value)}
          >
            <option value="REACHED">Reached</option>
            <option value="VOICEMAIL">Voicemail</option>
            <option value="NO_ANSWER">No Answer</option>
            <option value="NEEDS_CALL_BACK">Needs Call Back</option>
          </select>
        </div>

        <div className="form-group">
          <label>Patient Questions</label>
          <textarea
            className="form-control"
            rows={3}
            value={questions}
            onChange={(e) => setQuestions(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Next Steps</label>
          <textarea
            className="form-control"
            rows={2}
            value={nextSteps}
            onChange={(e) => setNextSteps(e.target.value)}
          />
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn btn-secondary"
            onClick={() => save(false)}
            disabled={saving}
          >
            Save Progress
          </button>
          <button
            className="btn btn-success"
            onClick={() => save(true)}
            disabled={saving || !reached}
          >
            Mark Complete
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Scheduling Tab ──────────────────────────────────────────────────── */
function SchedulingTab({
  caseId,
  schedule,
  onUpdate,
}: {
  caseId: string;
  schedule: Schedule | null;
  onUpdate: () => void;
}) {
  const [dateTime, setDateTime] = useState(
    schedule?.date_time ? schedule.date_time.slice(0, 16) : ""
  );
  const [location, setLocation] = useState(schedule?.location || "");
  const [duration, setDuration] = useState(
    schedule?.duration_minutes?.toString() || "120"
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await api.post(`/cases/${caseId}/schedule`, {
        date_time: new Date(dateTime).toISOString(),
        location: location || undefined,
        duration_minutes: duration ? parseInt(duration) : undefined,
      });
      onUpdate();
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      setError(detail || "Failed to save schedule.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <div className="card-title">Scheduling</div>
      {error && <div className="error-message mt-2">{error}</div>}

      {schedule && (
        <div
          style={{
            marginTop: 12,
            padding: 12,
            background: "#eff6ff",
            borderRadius: 6,
            color: "#1d4ed8",
          }}
        >
          Scheduled: {new Date(schedule.date_time).toLocaleString()} at{" "}
          {schedule.location || "TBD"} ({schedule.duration_minutes || "?"}min)
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <div className="grid-2">
          <div className="form-group">
            <label>Date & Time</label>
            <input
              type="datetime-local"
              className="form-control"
              value={dateTime}
              onChange={(e) => setDateTime(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Duration (minutes)</label>
            <input
              className="form-control"
              type="number"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
            />
          </div>
        </div>
        <div className="form-group">
          <label>Location</label>
          <input
            className="form-control"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" onClick={save} disabled={saving || !dateTime}>
          {schedule ? "Update Schedule" : "Set Schedule"}
        </button>
      </div>
    </div>
  );
}

/* ── Pharmacy Tab ────────────────────────────────────────────────────── */
function PharmacyTab({
  caseId,
  pharmacy,
  onUpdate,
}: {
  caseId: string;
  pharmacy: PharmacyOrder | null;
  onUpdate: () => void;
}) {
  const [shipTo, setShipTo] = useState(pharmacy?.ship_to || "");
  const [arrivalDate, setArrivalDate] = useState(
    pharmacy?.requested_arrival_date || ""
  );
  const [notes, setNotes] = useState(pharmacy?.pharmacy_notes || "");
  const [fulfillmentStatus, setFulfillmentStatus] = useState<string>(
    pharmacy?.fulfillment_status || "NOT_STARTED"
  );
  const [ndc, setNdc] = useState(pharmacy?.ndc || "");
  const [lot, setLot] = useState(pharmacy?.lot || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const push = async () => {
    setSaving(true);
    setError("");
    try {
      await api.post(`/cases/${caseId}/pharmacy-push`, {
        ship_to: shipTo || undefined,
        requested_arrival_date: arrivalDate || undefined,
        pharmacy_notes: notes || undefined,
      });
      onUpdate();
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      setError(detail || "Failed to push.");
    } finally {
      setSaving(false);
    }
  };

  const updateFulfillment = async () => {
    setSaving(true);
    setError("");
    try {
      await api.patch(`/cases/${caseId}/pharmacy-push`, {
        fulfillment_status: fulfillmentStatus,
        ndc: ndc || undefined,
        lot: lot || undefined,
      });
      onUpdate();
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      setError(detail || "Failed to update.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <div className="card-title">Pharmacy Push & Fulfillment</div>
      {error && <div className="error-message mt-2">{error}</div>}

      {!pharmacy ? (
        <div style={{ marginTop: 16 }}>
          <div className="form-group">
            <label>Ship To</label>
            <input
              className="form-control"
              value={shipTo}
              onChange={(e) => setShipTo(e.target.value)}
            />
          </div>
          <div className="grid-2">
            <div className="form-group">
              <label>Requested Arrival Date</label>
              <input
                type="date"
                className="form-control"
                value={arrivalDate}
                onChange={(e) => setArrivalDate(e.target.value)}
              />
            </div>
          </div>
          <div className="form-group">
            <label>Pharmacy Notes</label>
            <textarea
              className="form-control"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <button className="btn btn-primary" onClick={push} disabled={saving}>
            Push to Pharmacy
          </button>
        </div>
      ) : (
        <div style={{ marginTop: 16 }}>
          <div
            style={{
              padding: 12,
              background: "#eff6ff",
              borderRadius: 6,
              color: "#1d4ed8",
              marginBottom: 16,
            }}
          >
            Pushed at: {new Date(pharmacy.pushed_at!).toLocaleString()}
            <br />
            Ship to: {pharmacy.ship_to || "N/A"}
            <br />
            Current fulfillment: <strong>{pharmacy.fulfillment_status}</strong>
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label>Fulfillment Status</label>
              <select
                className="form-control"
                value={fulfillmentStatus}
                onChange={(e) => setFulfillmentStatus(e.target.value)}
              >
                <option value="NOT_STARTED">Not Started</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="READY">Ready</option>
                <option value="SHIPPED">Shipped</option>
                <option value="RECEIVED">Received</option>
              </select>
            </div>
            <div className="form-group">
              <label>NDC</label>
              <input
                className="form-control"
                value={ndc}
                onChange={(e) => setNdc(e.target.value)}
              />
            </div>
          </div>
          <div className="form-group">
            <label>Lot Number</label>
            <input
              className="form-control"
              value={lot}
              onChange={(e) => setLot(e.target.value)}
            />
          </div>
          <button
            className="btn btn-primary"
            onClick={updateFulfillment}
            disabled={saving}
          >
            Update Fulfillment
          </button>
        </div>
      )}
    </div>
  );
}

/* ── Tasks Tab ───────────────────────────────────────────────────────── */
function TasksTab({
  caseId,
  tasks,
  onUpdate,
}: {
  caseId: string;
  tasks: TaskType[];
  onUpdate: () => void;
}) {
  const [showCreate, setShowCreate] = useState(false);
  const [newType, setNewType] = useState("GENERAL");
  const [saving, setSaving] = useState(false);

  const createTask = async () => {
    setSaving(true);
    try {
      await api.post(`/cases/${caseId}/tasks`, {
        type: newType,
        payload_json: {},
      });
      setShowCreate(false);
      onUpdate();
    } catch {
      /* ignore */
    } finally {
      setSaving(false);
    }
  };

  const updateTaskStatus = async (taskId: string, status: TaskStatus) => {
    try {
      await api.patch(`/tasks/${taskId}`, { status });
      onUpdate();
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Tasks</div>
        <button
          className="btn btn-primary btn-sm"
          onClick={() => setShowCreate(!showCreate)}
        >
          + Add Task
        </button>
      </div>

      {showCreate && (
        <div
          style={{
            padding: 12,
            background: "#f8fafc",
            borderRadius: 6,
            marginBottom: 16,
          }}
        >
          <div className="form-group">
            <label>Task Type</label>
            <select
              className="form-control"
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
            >
              <option value="GENERAL">General</option>
              <option value="CLINICAL_REVIEW">Clinical Review</option>
              <option value="BENEFITS_INVESTIGATION">Benefits Investigation</option>
              <option value="PRIOR_AUTH">Prior Auth</option>
              <option value="FINANCIAL_COUNSELING">Financial Counseling</option>
              <option value="WELCOME_CALL">Welcome Call</option>
              <option value="SCHEDULING">Scheduling</option>
              <option value="PHARMACY_PUSH">Pharmacy Push</option>
              <option value="DOCUMENT_REQUEST">Document Request</option>
            </select>
          </div>
          <button
            className="btn btn-primary btn-sm"
            onClick={createTask}
            disabled={saving}
          >
            Create
          </button>
        </div>
      )}

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td>{t.type.replace(/_/g, " ")}</td>
                <td>
                  <span
                    className="status-badge"
                    style={{
                      background:
                        t.status === "DONE"
                          ? "#10b981"
                          : t.status === "IN_PROGRESS"
                          ? "#3b82f6"
                          : "#94a3b8",
                    }}
                  >
                    {t.status}
                  </span>
                </td>
                <td>
                  {t.status !== "DONE" && t.status !== "CANCELLED" && (
                    <div style={{ display: "flex", gap: 4 }}>
                      {t.status === "PENDING" && (
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => updateTaskStatus(t.id, "IN_PROGRESS")}
                        >
                          Start
                        </button>
                      )}
                      <button
                        className="btn btn-success btn-sm"
                        onClick={() => updateTaskStatus(t.id, "DONE")}
                      >
                        Done
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {tasks.length === 0 && (
              <tr>
                <td colSpan={3} style={{ textAlign: "center" }}>
                  No tasks yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Documents Tab ───────────────────────────────────────────────────── */
function DocumentsTab({
  caseId,
  documents,
  onUpdate,
}: {
  caseId: string;
  documents: Document[];
  onUpdate: () => void;
}) {
  const [fileName, setFileName] = useState("");
  const [fileType, setFileType] = useState("");
  const [uploading, setUploading] = useState(false);

  const upload = async () => {
    if (!fileName) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file_name", fileName);
      form.append("file_type", fileType || "application/pdf");
      await api.post(`/cases/${caseId}/documents`, form);
      setFileName("");
      setFileType("");
      onUpdate();
    } catch {
      /* ignore */
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-title">Documents</div>

      <div
        style={{
          marginTop: 16,
          padding: 12,
          background: "#f8fafc",
          borderRadius: 6,
          marginBottom: 16,
        }}
      >
        <div className="grid-2">
          <div className="form-group">
            <label>File Name</label>
            <input
              className="form-control"
              value={fileName}
              onChange={(e) => setFileName(e.target.value)}
              placeholder="referral.pdf"
            />
          </div>
          <div className="form-group">
            <label>File Type</label>
            <input
              className="form-control"
              value={fileType}
              onChange={(e) => setFileType(e.target.value)}
              placeholder="application/pdf"
            />
          </div>
        </div>
        <button
          className="btn btn-primary btn-sm"
          onClick={upload}
          disabled={uploading || !fileName}
        >
          Upload Document
        </button>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>File</th>
              <th>Type</th>
              <th>Uploaded</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td>{d.file_name}</td>
                <td>{d.file_type || "N/A"}</td>
                <td>{new Date(d.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr>
                <td colSpan={3} style={{ textAlign: "center" }}>
                  No documents uploaded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Claim Case Bar ──────────────────────────────────────────────────── */
function ClaimCaseBar({
  caseId,
  userOrgId,
  onClaimed,
}: {
  caseId: string;
  userOrgId: string;
  onClaimed: () => void;
}) {
  const [claiming, setClaiming] = useState(false);
  const [error, setError] = useState("");

  const claim = async () => {
    setClaiming(true);
    setError("");
    try {
      await api.post(`/cases/${caseId}/assign-infusion-org`, {
        infusion_org_id: userOrgId,
      });
      onClaimed();
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      setError(detail || "Failed to claim case.");
    } finally {
      setClaiming(false);
    }
  };

  return (
    <div
      style={{
        marginTop: 12,
        padding: 12,
        background: "#fef9c3",
        borderRadius: 6,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <span style={{ color: "#92400e", fontWeight: 500, fontSize: 14 }}>
        This case is unassigned. Claim it to start processing.
      </span>
      <button
        className="btn btn-primary btn-sm"
        onClick={claim}
        disabled={claiming}
      >
        {claiming ? "Claiming..." : "Claim Case"}
      </button>
      {error && (
        <span style={{ color: "var(--danger)", fontSize: 13, marginLeft: 8 }}>
          {error}
        </span>
      )}
    </div>
  );
}

/* ── Timeline Tab ────────────────────────────────────────────────────── */
function TimelineTab({ timeline }: { timeline: TimelineEvent[] }) {
  return (
    <div className="card">
      <div className="card-title">Activity Timeline</div>
      <div className="timeline" style={{ marginTop: 16 }}>
        {timeline.map((e) => (
          <div key={e.id} className="timeline-item">
            <div className="timeline-dot" />
            <div className="timeline-content">
              <div className="timeline-event-type">
                {e.event_type.replace(/_/g, " ")}
              </div>
              <div className="timeline-time">
                {new Date(e.created_at).toLocaleString()}
              </div>
              {e.metadata_json && Object.keys(e.metadata_json).length > 0 && (
                <div className="timeline-meta">
                  {Object.entries(e.metadata_json).map(([k, v]) => (
                    <span key={k} style={{ marginRight: 12 }}>
                      {k}: {typeof v === "string" ? v.replace(/_/g, " ") : JSON.stringify(v)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {timeline.length === 0 && (
          <div className="text-muted">No activity yet.</div>
        )}
      </div>
    </div>
  );
}
