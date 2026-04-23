import { useEffect, useMemo, useState } from "react";

const TABS = ["Runbooks", "Incidents", "Approvals", "Audit"];

export default function App() {
  const [baseUrl, setBaseUrl] = useState("http://localhost:8080");
  const [apiKey, setApiKey] = useState("admin-dev-key");
  const [activeTab, setActiveTab] = useState(TABS[0]);

  const [providers, setProviders] = useState([]);
  const [tasks, setTasks] = useState([]);

  const [taskProvider, setTaskProvider] = useState("aws");
  const [taskName, setTaskName] = useState("check_instance_status");
  const [resourceId, setResourceId] = useState("");
  const [taskLimit, setTaskLimit] = useState(10);
  const [taskResponse, setTaskResponse] = useState(null);

  const [incidentProvider, setIncidentProvider] = useState("aws");
  const [incidentTitle, setIncidentTitle] = useState("High API latency");
  const [incidentDescription, setIncidentDescription] = useState("p95 latency increased after deploy");
  const [incidentLogs, setIncidentLogs] = useState("timeout and connection reset observed");
  const [incidentResponse, setIncidentResponse] = useState(null);

  const [approvals, setApprovals] = useState([]);
  const [reviewNote, setReviewNote] = useState("Approved after service impact check.");
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const headers = useMemo(
    () => ({
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    }),
    [apiKey]
  );

  async function callApi(path, options = {}) {
    const response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers: {
        ...headers,
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${detail}`);
    }

    return response.json();
  }

  async function bootstrap() {
    setLoading(true);
    setError("");
    try {
      const providersResult = await callApi("/providers");
      const tasksResult = await callApi("/tasks");
      setProviders(providersResult.providers || []);
      setTasks(tasksResult.tasks || []);
      if (providersResult.providers?.length) {
        setTaskProvider(providersResult.providers[0]);
        setIncidentProvider(providersResult.providers[0]);
      }
      if (tasksResult.tasks?.length) {
        setTaskName(tasksResult.tasks[0].name);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function executeTask() {
    setLoading(true);
    setError("");
    try {
      const data = await callApi("/tasks/execute", {
        method: "POST",
        body: JSON.stringify({
          provider: taskProvider,
          task: taskName,
          resource_id: resourceId || null,
          params: { limit: Number(taskLimit) },
        }),
      });
      setTaskResponse(data);
      await Promise.all([refreshApprovals(), refreshAudit()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function triageIncident() {
    setLoading(true);
    setError("");
    try {
      const data = await callApi("/incidents/triage", {
        method: "POST",
        body: JSON.stringify({
          provider: incidentProvider,
          title: incidentTitle,
          description: incidentDescription,
          logs: incidentLogs,
        }),
      });
      setIncidentResponse(data);
      await refreshAudit();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function refreshApprovals() {
    try {
      const data = await callApi("/approvals?status=pending&limit=200");
      setApprovals(data.approvals || []);
    } catch (err) {
      setError(err.message);
    }
  }

  async function reviewApproval(approvalId, approve) {
    setLoading(true);
    setError("");
    try {
      await callApi(`/approvals/${approvalId}/review`, {
        method: "POST",
        body: JSON.stringify({
          approve,
          note: reviewNote,
          execute_on_approve: true,
        }),
      });
      await Promise.all([refreshApprovals(), refreshAudit()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function refreshAudit() {
    try {
      const data = await callApi("/audit/logs?limit=200");
      setAudit(data || []);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    bootstrap();
  }, []);

  return (
    <div className="shell">
      <div className="bg-orb orb-a" />
      <div className="bg-orb orb-b" />
      <header className="topbar">
        <h1>AI Ops Hub</h1>
        <p>Multi-cloud L1/L2 operations center</p>
      </header>

      <section className="connection card">
        <label>
          API Base URL
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
        </label>
        <label>
          X-API-Key
          <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
        </label>
        <button onClick={bootstrap} disabled={loading}>
          Connect
        </button>
      </section>

      <nav className="tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            className={tab === activeTab ? "tab tab-active" : "tab"}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      {error ? <div className="error">{error}</div> : null}

      {activeTab === "Runbooks" && (
        <section className="card grid-two">
          <div>
            <h2>Execute Task</h2>
            <label>
              Provider
              <select value={taskProvider} onChange={(e) => setTaskProvider(e.target.value)}>
                {providers.map((provider) => (
                  <option key={provider}>{provider}</option>
                ))}
              </select>
            </label>
            <label>
              Task
              <select value={taskName} onChange={(e) => setTaskName(e.target.value)}>
                {tasks.map((task) => (
                  <option key={task.name}>{task.name}</option>
                ))}
              </select>
            </label>
            <label>
              Resource ID
              <input value={resourceId} onChange={(e) => setResourceId(e.target.value)} />
            </label>
            <label>
              Event Limit
              <input
                type="number"
                value={taskLimit}
                onChange={(e) => setTaskLimit(e.target.value)}
              />
            </label>
            <button onClick={executeTask} disabled={loading}>
              Run Task
            </button>
          </div>
          <pre>{taskResponse ? JSON.stringify(taskResponse, null, 2) : "No task run yet."}</pre>
        </section>
      )}

      {activeTab === "Incidents" && (
        <section className="card grid-two">
          <div>
            <h2>Incident Triage</h2>
            <label>
              Provider
              <select value={incidentProvider} onChange={(e) => setIncidentProvider(e.target.value)}>
                {providers.map((provider) => (
                  <option key={provider}>{provider}</option>
                ))}
              </select>
            </label>
            <label>
              Title
              <input value={incidentTitle} onChange={(e) => setIncidentTitle(e.target.value)} />
            </label>
            <label>
              Description
              <textarea
                value={incidentDescription}
                onChange={(e) => setIncidentDescription(e.target.value)}
              />
            </label>
            <label>
              Logs
              <textarea value={incidentLogs} onChange={(e) => setIncidentLogs(e.target.value)} />
            </label>
            <button onClick={triageIncident} disabled={loading}>
              Triage
            </button>
          </div>
          <pre>{incidentResponse ? JSON.stringify(incidentResponse, null, 2) : "No triage run yet."}</pre>
        </section>
      )}

      {activeTab === "Approvals" && (
        <section className="card">
          <div className="row">
            <h2>Pending Approvals</h2>
            <button onClick={refreshApprovals} disabled={loading}>
              Refresh
            </button>
          </div>
          <label>
            Review Note
            <input value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} />
          </label>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Provider</th>
                  <th>Task</th>
                  <th>Requested By</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {approvals.length === 0 && (
                  <tr>
                    <td colSpan={5}>No pending approvals.</td>
                  </tr>
                )}
                {approvals.map((approval) => (
                  <tr key={approval.id}>
                    <td>{approval.id.slice(0, 8)}</td>
                    <td>{approval.provider}</td>
                    <td>{approval.task}</td>
                    <td>{approval.requested_by_role}</td>
                    <td className="actions">
                      <button onClick={() => reviewApproval(approval.id, true)} disabled={loading}>
                        Approve
                      </button>
                      <button onClick={() => reviewApproval(approval.id, false)} disabled={loading}>
                        Reject
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === "Audit" && (
        <section className="card">
          <div className="row">
            <h2>Audit Trail</h2>
            <button onClick={refreshAudit} disabled={loading}>
              Refresh
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Role</th>
                  <th>Action</th>
                  <th>Task</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {audit.length === 0 && (
                  <tr>
                    <td colSpan={5}>No audit events yet.</td>
                  </tr>
                )}
                {audit.map((entry) => (
                  <tr key={entry.id}>
                    <td>{entry.timestamp}</td>
                    <td>{entry.actor_role}</td>
                    <td>{entry.action}</td>
                    <td>{entry.task || "-"}</td>
                    <td>{entry.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
