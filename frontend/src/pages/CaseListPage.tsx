import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../AuthContext";
import type { CaseSummary, CaseStatus } from "../types";
import { STATUS_LABELS, STATUS_COLORS } from "../types";

const ALL_STATUSES: CaseStatus[] = [
  "REFERRAL_RECEIVED",
  "CLINICAL_COMPLETENESS_CHECK",
  "BENEFITS_INVESTIGATION",
  "PRIOR_AUTH_SUBMITTED",
  "PRIOR_AUTH_APPROVED",
  "FINANCIAL_COUNSELING_PENDING",
  "FINANCIAL_CLEARED",
  "WELCOME_CALL_PENDING",
  "WELCOME_CALL_COMPLETED",
  "SCHEDULING_READY",
  "SCHEDULED",
  "PHARMACY_PUSH_PENDING",
  "PHARMACY_PUSHED",
  "DRUG_FULFILLMENT_IN_PROGRESS",
  "DRUG_READY",
  "INFUSION_COMPLETED",
  "ON_THERAPY",
  "DISCONTINUED",
];

export default function CaseListPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);
  const { user } = useAuth();
  const navigate = useNavigate();

  const loadCases = async () => {
    const params: Record<string, string> = {};
    if (statusFilter) params.status_filter = statusFilter;
    const res = await api.get("/cases", { params });
    setCases(res.data);
  };

  useEffect(() => {
    loadCases();
  }, [statusFilter]);

  const isProvider = user?.role === "PROVIDER";

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">
          {isProvider ? "My Referrals" : "Intake Queue"}
        </h1>
        {isProvider && (
          <button
            className="btn btn-primary"
            onClick={() => setShowCreate(true)}
          >
            + New Referral
          </button>
        )}
      </div>

      <div className="filter-bar">
        <select
          className="form-control"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          {ALL_STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
        <span className="text-muted">{cases.length} cases</span>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Patient</th>
              <th>Status</th>
              <th>Created</th>
              <th>ID</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr
                key={c.id}
                className="clickable"
                onClick={() => navigate(`/cases/${c.id}`)}
              >
                <td>
                  {c.patient
                    ? `${c.patient.first_name} ${c.patient.last_name}`
                    : "No patient"}
                </td>
                <td>
                  <span
                    className="status-badge"
                    style={{ background: STATUS_COLORS[c.status] }}
                  >
                    {STATUS_LABELS[c.status]}
                  </span>
                </td>
                <td>{new Date(c.created_at).toLocaleDateString()}</td>
                <td className="text-muted">{c.id.slice(0, 8)}...</td>
              </tr>
            ))}
            {cases.length === 0 && (
              <tr>
                <td colSpan={4} style={{ textAlign: "center", padding: 40 }}>
                  No cases found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateReferralModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            loadCases();
          }}
        />
      )}
    </div>
  );
}

function CreateReferralModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [dob, setDob] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [drugName, setDrugName] = useState("");
  const [dose, setDose] = useState("");
  const [frequency, setFrequency] = useState("");
  const [route, setRoute] = useState("IV");
  const [icd10, setIcd10] = useState("");
  const [payerName, setPayerName] = useState("");
  const [memberId, setMemberId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!firstName || !lastName) {
      setError("Patient first and last name are required.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const caseRes = await api.post("/cases", {
        patient: {
          first_name: firstName,
          last_name: lastName,
          dob: dob || undefined,
          phone: phone || undefined,
          email: email || undefined,
        },
      });
      const caseId = caseRes.data.id;

      if (drugName || dose || frequency) {
        await api.patch(`/cases/${caseId}/prescription`, {
          drug_name: drugName || undefined,
          dose: dose || undefined,
          frequency: frequency || undefined,
          route: route || undefined,
          diagnosis_icd10: icd10 || undefined,
        });
      }

      if (payerName || memberId) {
        await api.patch(`/cases/${caseId}/insurance`, {
          payer_name: payerName || undefined,
          member_id: memberId || undefined,
          group_id: groupId || undefined,
        });
      }

      onCreated();
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : undefined;
      setError(msg || "Failed to create referral.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">New Referral</h2>
        {error && <div className="error-message">{error}</div>}

        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Patient Information</h3>
        <div className="grid-2">
          <div className="form-group">
            <label>First Name *</label>
            <input
              className="form-control"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Last Name *</label>
            <input
              className="form-control"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
          </div>
        </div>
        <div className="grid-2">
          <div className="form-group">
            <label>Date of Birth</label>
            <input
              type="date"
              className="form-control"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Phone</label>
            <input
              className="form-control"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
        </div>
        <div className="form-group">
          <label>Email</label>
          <input
            className="form-control"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <h3 style={{ fontSize: 14, marginBottom: 12, marginTop: 16 }}>
          Prescription
        </h3>
        <div className="grid-2">
          <div className="form-group">
            <label>Drug Name</label>
            <input
              className="form-control"
              value={drugName}
              onChange={(e) => setDrugName(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Dose</label>
            <input
              className="form-control"
              value={dose}
              onChange={(e) => setDose(e.target.value)}
            />
          </div>
        </div>
        <div className="grid-2">
          <div className="form-group">
            <label>Frequency</label>
            <input
              className="form-control"
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Route</label>
            <select
              className="form-control"
              value={route}
              onChange={(e) => setRoute(e.target.value)}
            >
              <option value="IV">IV</option>
              <option value="SubQ">SubQ</option>
              <option value="IM">IM</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label>Diagnosis (ICD-10)</label>
          <input
            className="form-control"
            value={icd10}
            onChange={(e) => setIcd10(e.target.value)}
          />
        </div>

        <h3 style={{ fontSize: 14, marginBottom: 12, marginTop: 16 }}>
          Insurance
        </h3>
        <div className="grid-2">
          <div className="form-group">
            <label>Payer Name</label>
            <input
              className="form-control"
              value={payerName}
              onChange={(e) => setPayerName(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Member ID</label>
            <input
              className="form-control"
              value={memberId}
              onChange={(e) => setMemberId(e.target.value)}
            />
          </div>
        </div>
        <div className="form-group">
          <label>Group ID</label>
          <input
            className="form-control"
            value={groupId}
            onChange={(e) => setGroupId(e.target.value)}
          />
        </div>

        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? "Creating..." : "Submit Referral"}
          </button>
        </div>
      </div>
    </div>
  );
}
