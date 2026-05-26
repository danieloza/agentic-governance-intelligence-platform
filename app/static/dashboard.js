const state = {
  currentView: "overview",
  search: "",
  manifest: null,
  overview: null,
  observability: null,
  agents: [],
  audit: [],
  incidents: [],
  regressionCases: [],
  platformRegression: null,
  openapi: null,
};

const viewMeta = {
  overview: ["Governance Overview", "Monitor governed agents, scoped tools, policy decisions and runtime evidence."],
  agents: ["Agents", "Registered agents, ownership, approval status, scopes and revocation state."],
  tools: ["Tool Gateway", "Controlled business and developer tools protected by scoped access."],
  policies: ["Policy Decisions", "Default-deny decisions, required scopes, reasons and live policy preview."],
  incidents: ["Incidents", "Denied, risky or redacted events prepared for operator review."],
  regression: ["Regression Lab", "Scenario checks that validate expected allow/deny behavior before rollout."],
  audit: ["Audit Explorer", "Reviewable evidence stream for registrations, approvals, tokens and tool calls."],
  openapi: ["OpenAPI Console", "Endpoint explorer generated from the FastAPI OpenAPI schema."],
  observability: ["Observability", "Aggregate health, tool-call, incident, redaction and scope metrics."],
};

const qs = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadJson(url, fallback = null) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(await response.text());
    return await response.json();
  } catch (error) {
    if (fallback !== null) return fallback;
    throw error;
  }
}

async function bootstrap() {
  bindEvents();
  await refreshData();
  setView(location.hash.replace("#", "") || "overview", { replaceHash: true });
}

async function refreshData() {
  const [manifest, overview, observability, agents, audit, incidents, regressionCases, platformRegression, openapi] =
    await Promise.all([
      loadJson("/.well-known/agent-auth.json", {}),
      loadJson("/platform/overview", {}),
      loadJson("/observability/summary", {}),
      loadJson("/dashboard/access-requests", { rows: [] }),
      loadJson("/agent-auth/audit", []),
      loadJson("/incidents", []),
      loadJson("/regression/cases", []),
      loadJson("/platform/regression", { runs: [], metrics: {} }),
      loadJson("/openapi.json", { paths: {} }),
    ]);

  state.manifest = manifest;
  state.overview = overview;
  state.observability = observability;
  state.agents = agents.rows || [];
  state.audit = audit;
  state.incidents = incidents;
  state.regressionCases = regressionCases;
  state.platformRegression = platformRegression;
  state.openapi = openapi;
  renderStatus();
  renderMetrics();
}

function bindEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", (event) => {
      const view = event.currentTarget.dataset.view;
      if (view) setView(view);
    });
  });
  qs("refresh-button").addEventListener("click", async () => {
    await refreshData();
    setView(state.currentView, { replaceHash: true });
  });
  qs("global-search").addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    setView(state.currentView, { replaceHash: true });
  });
  window.addEventListener("hashchange", () => setView(location.hash.replace("#", "") || "overview", { replaceHash: true }));
}

function setView(view, options = {}) {
  if (!viewMeta[view]) view = "overview";
  state.currentView = view;
  if (!options.replaceHash) location.hash = view;
  document.querySelectorAll("[data-view]").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  const [title, subtitle] = viewMeta[view];
  qs("view-title").textContent = title;
  qs("view-subtitle").textContent = subtitle;
  renderView(view);
}

function renderStatus() {
  qs("env-value").textContent = "local";
  qs("policy-value").textContent = state.manifest?.policy_rules?.default_deny ? "default-deny" : "unknown";
  const health = Number(state.overview?.metrics?.runtime_health || 0);
  qs("health-value").textContent = health >= 90 ? "operational" : "degraded";
}

function renderMetrics() {
  const m = state.overview?.metrics || {};
  const o = state.observability || {};
  const cards = [
    ["Total Agents", o.total_agents ?? m.total_agents ?? 0, `${o.approved_agents ?? m.active_agents ?? 0} approved`, "info"],
    ["Tool Calls", o.total_tool_calls ?? m.total_activity ?? 0, `${o.denied_tool_calls ?? m.denied_tool_calls ?? 0} denied`, "violet"],
    ["Open Incidents", o.open_incidents ?? state.incidents.filter((item) => item.status === "open").length, "operator review queue", "bad"],
    ["Policy Violations", m.policy_violations ?? deniedLogs().length, "default-deny evidence", "warn"],
    ["Redaction Events", o.redaction_events ?? state.audit.filter((log) => log.pii_redacted).length, "PII/secret safe", "good"],
    ["Runtime Health", `${m.runtime_health ?? 100}%`, "system operational", "good"],
  ];
  qs("metric-grid").innerHTML = cards.map(([label, value, foot, klass]) => `
    <article class="metric-card">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value ${klass}">${escapeHtml(value)}</div>
      <div class="metric-foot">${escapeHtml(foot)}</div>
    </article>
  `).join("");
}

function renderView(view) {
  const renderers = {
    overview: renderOverview,
    agents: renderAgents,
    tools: renderTools,
    policies: renderPolicies,
    incidents: renderIncidents,
    regression: renderRegression,
    audit: renderAudit,
    openapi: renderOpenApi,
    observability: renderObservability,
  };
  try {
    qs("view-grid").innerHTML = renderers[view]();
  } catch (error) {
    qs("view-grid").innerHTML = panel("View failed to load", `<p class="panel-subtitle">${escapeHtml(error.message || error)}</p>`, "panel-full");
  }
}

function panel(title, body, klass = "") {
  return `<section class="panel ${klass}"><div class="panel-head"><div><h2>${escapeHtml(title)}</h2></div></div>${body}</section>`;
}

function filtered(rows, fields) {
  if (!state.search) return rows;
  return rows.filter((row) => fields.some((field) => String(row[field] ?? "").toLowerCase().includes(state.search)));
}

function deniedLogs() {
  return state.audit.filter((log) => log.decision === "denied" || log.action === "policy_failure");
}

function toolLogs() {
  return state.audit.filter((log) => log.tool_name);
}

function renderOverview() {
  return [
    panel("Agent Status Table", agentTable(state.agents.slice(0, 6)), "panel-wide"),
    panel("Live Policy Preview", livePolicyPreview(), ""),
    panel("Tool Call Timeline", timeline(toolLogs().slice(0, 8)), ""),
    panel("Policy Decision Panel", policyDecisionPanel(), "panel-wide"),
    panel("Incident Severity", incidentCards(), ""),
    panel("Regression Test Results", regressionPreview(), ""),
    panel("Audit Log Explorer", auditPreview(), "panel-wide"),
    panel("OpenAPI Endpoint Explorer", openApiPreview(), ""),
  ].join("");
}

function renderAgents() {
  return [
    panel("Registered Agents", agentTable(filtered(state.agents, ["agent_name", "agent_type", "owner_user_id", "status"])), "panel-full"),
    panel("Agent Approval Mix", approvalMix(), ""),
    panel("Scope Coverage", scopeBars(), "panel-wide"),
  ].join("");
}

function renderTools() {
  const tools = Object.entries(state.openapi?.paths || {})
    .filter(([path]) => path.startsWith("/tools/"))
    .map(([path, methods]) => ({ path, method: Object.keys(methods)[0]?.toUpperCase() || "POST" }));
  return [
    panel("Controlled Tool Gateway", endpointList(tools), "panel-wide"),
    panel("Tool Call Timeline", timeline(toolLogs().slice(0, 10)), ""),
    panel("Gateway Controls", gatewayControls(), ""),
    panel("Most Used Tools", mostUsedTools(), "panel-wide"),
  ].join("");
}

function renderPolicies() {
  return [
    panel("Policy Decision Panel", policyDecisionPanel(), "panel-wide"),
    panel("Live Policy Preview", livePolicyPreview(), ""),
    panel("Denied Decisions", auditTable(deniedLogs()), "panel-full"),
  ].join("");
}

function renderIncidents() {
  const liveIncidents = state.incidents.length
    ? state.incidents.map((item) => [item.title, item.severity, item.status, item.policy_reason])
    : (state.overview?.incidents || []).map((item) => [item.title, item.severity, "open", item.module]);
  return [
    panel("Incident Severity Cards", incidentCards(), "panel-wide"),
    panel("Incident Queue", table(["Incident", "Severity", "Status", "Reason"], liveIncidents), "panel-full"),
    panel("Review Workflow", reviewWorkflow(), ""),
  ].join("");
}

function renderRegression() {
  const stored = state.regressionCases.map((item) => [item.name, item.requested_tool, item.expected_decision, item.expected_reason_contains]);
  const platform = (state.platformRegression?.runs || []).map((item) => [item.scenario, item.candidate, item.verdict, `${item.latency_delta}% latency`]);
  return [
    panel("Regression Test Results", regressionPreview(), ""),
    panel("Stored Regression Cases", table(["Name", "Requested Tool", "Expected", "Reason Contains"], stored), "panel-wide"),
    panel("Scenario History", table(["Scenario", "Candidate", "Verdict", "Delta"], platform), "panel-full"),
  ].join("");
}

function renderAudit() {
  return [
    panel("Audit Explorer", auditTable(filtered(state.audit, ["action", "tool_name", "requested_scope", "decision", "reason"])), "panel-full"),
    panel("Decision Mix", decisionDonut(), ""),
    panel("Audit Signals", auditSignals(), "panel-wide"),
  ].join("");
}

function renderOpenApi() {
  const endpoints = Object.entries(state.openapi?.paths || {}).flatMap(([path, methods]) =>
    Object.keys(methods).map((method) => ({ path, method: method.toUpperCase(), tag: methods[method].tags?.[0] || "API" }))
  );
  return [
    panel("OpenAPI Endpoint Explorer", endpointList(filtered(endpoints, ["path", "method", "tag"])), "panel-wide"),
    panel("Developer Console", openApiConsole(), ""),
    panel("Primary Flow", primaryFlow(), "panel-full"),
  ].join("");
}

function renderObservability() {
  const o = state.observability || {};
  return [
    panel("Observability Summary", observabilityGrid(), "panel-wide"),
    panel("Activity Trend", lineChart(), ""),
    panel("Most Requested Scopes", scopeBars(), "panel-wide"),
    panel("Most Used Tools", mostUsedTools(), ""),
  ].join("");
}

function agentTable(rows) {
  return table(
    ["Agent", "Type", "Owner", "Status", "Requested Scopes"],
    rows.map((row) => [
      row.agent_name,
      row.agent_type,
      row.owner_user_id,
      chip(row.status),
      (row.requested_scopes || []).join(", "),
    ]),
    true
  );
}

function auditTable(rows) {
  return table(
    ["Action", "Tool", "Scope", "Decision", "Reason"],
    rows.map((log) => [
      log.action,
      log.tool_name || "agent-auth",
      log.requested_scope || "n/a",
      chip(log.decision),
      log.reason,
    ]),
    true
  );
}

function table(headers, rows, rawHtml = false) {
  if (!rows.length) return `<div class="empty">No rows match the current filters.</div>`;
  return `
    <div class="table-wrap">
      <table class="table">
        <thead><tr>${headers.map((head) => `<th>${escapeHtml(head)}</th>`).join("")}</tr></thead>
        <tbody>
          ${rows.map((row) => `<tr>${row.map((cell) => `<td>${rawHtml && String(cell).startsWith("<") ? cell : escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function chip(value) {
  const normalized = String(value || "info").replace("pending_approval", "pending").toLowerCase();
  return `<span class="chip ${escapeHtml(normalized)}">${escapeHtml(normalized)}</span>`;
}

function timeline(rows) {
  if (!rows.length) return `<div class="empty">No tool calls yet. Trigger a governed tool endpoint to populate this timeline.</div>`;
  return `<div class="timeline">${rows.map((log) => `
    <div class="timeline-item">
      <span class="timeline-dot"></span>
      <div>
        <div class="timeline-title">${escapeHtml(log.tool_name || log.action)}</div>
        <div class="timeline-meta">${escapeHtml(log.requested_scope || "scope n/a")} - ${escapeHtml(log.reason)}</div>
      </div>
      ${chip(log.decision)}
    </div>
  `).join("")}</div>`;
}

function livePolicyPreview() {
  const sampleTool = "finance.get_invoice_summary";
  const required = "finance:invoice:read";
  const hasAgent = state.agents.some((agent) => (agent.approved_scopes || []).includes(required));
  const rows = [
    ["Tool mapping", sampleTool, "required scope exists"],
    ["Default deny", "enabled", "unknown tools blocked"],
    ["Human approval", hasAgent ? "satisfied" : "missing", "agent must be approved"],
    ["PII redaction", "enabled", "responses and logs are masked"],
  ];
  return `<div class="policy-preview">${rows.map(([title, value, meta]) => `
    <div class="preview-row">
      <div><strong>${escapeHtml(title)}</strong><small>${escapeHtml(meta)}</small></div>
      <span class="chip ${value === "missing" ? "high" : "allowed"}">${escapeHtml(value)}</span>
    </div>
  `).join("")}</div>`;
}

function policyDecisionPanel() {
  const rows = state.audit.slice(0, 8).map((log) => [
    log.tool_name || "agent-auth",
    log.requested_scope || "n/a",
    chip(log.decision),
    log.reason,
  ]);
  return table(["Surface", "Required Scope", "Decision", "Policy Reason"], rows, true);
}

function incidentCards() {
  const source = state.incidents.length ? state.incidents : [];
  const counts = {
    high: source.filter((item) => item.severity === "high").length,
    medium: source.filter((item) => item.severity === "medium").length,
    low: source.filter((item) => item.severity === "low").length,
    open: source.filter((item) => item.status === "open").length,
  };
  if (!source.length && state.overview?.metrics) {
    counts.high = state.overview.metrics.policy_violations || 0;
    counts.medium = state.overview.metrics.incidents_7d || 0;
    counts.low = 0;
    counts.open = counts.high + counts.medium;
  }
  return `
    <div class="policy-preview">
      <div class="preview-row"><div><strong>High severity</strong><small>blocked, dangerous or unauthorized actions</small></div>${chip(counts.high ? "high" : "low")}</div>
      <div class="preview-row"><div><strong>Medium severity</strong><small>requires operator review</small></div>${chip(counts.medium ? "medium" : "low")}</div>
      <div class="preview-row"><div><strong>Low severity</strong><small>informational governance signal</small></div>${chip(counts.low ? "open" : "low")}</div>
      <div class="preview-row"><div><strong>Open incidents</strong><small>items currently unresolved</small></div>${chip(counts.open ? "open" : "resolved")}</div>
    </div>
  `;
}

function regressionPreview() {
  const metrics = state.platformRegression?.metrics || {};
  const stable = metrics.stable || state.regressionCases.filter((item) => item.expected_decision === "allowed").length;
  const regression = metrics.regression || state.regressionCases.filter((item) => item.expected_decision === "denied").length;
  return `
    <div class="policy-preview">
      <div class="preview-row"><div><strong>Stable cases</strong><small>expected decision still matches policy</small></div><span class="metric-value good">${stable}</span></div>
      <div class="preview-row"><div><strong>Regressions</strong><small>candidate behavior requires review</small></div><span class="metric-value bad">${regression}</span></div>
      <div class="preview-row"><div><strong>Stored cases</strong><small>cases from /regression/cases</small></div><span class="metric-value info">${state.regressionCases.length}</span></div>
    </div>
  `;
}

function auditPreview() {
  return auditTable(state.audit.slice(0, 6));
}

function openApiPreview() {
  const endpoints = Object.entries(state.openapi?.paths || {}).slice(0, 8).map(([path, methods]) => ({
    path,
    method: Object.keys(methods)[0]?.toUpperCase() || "GET",
  }));
  return endpointList(endpoints);
}

function endpointList(items) {
  if (!items.length) return `<div class="empty">OpenAPI schema is empty or unavailable.</div>`;
  return `<div class="endpoint-grid">${items.map((item) => `
    <div class="endpoint">
      <span class="method">${escapeHtml(item.method)}</span>
      <span class="path">${escapeHtml(item.path)}${item.tag ? ` · ${escapeHtml(item.tag)}` : ""}</span>
    </div>
  `).join("")}</div>`;
}

function gatewayControls() {
  return `
    <div class="policy-preview">
      <div class="preview-row"><div><strong>Authenticate token</strong><small>agent_scoped_token required</small></div>${chip("allowed")}</div>
      <div class="preview-row"><div><strong>Scope to tool map</strong><small>tool must map to required scope</small></div>${chip("allowed")}</div>
      <div class="preview-row"><div><strong>Redact response</strong><small>PII and secrets are masked</small></div>${chip("allowed")}</div>
      <div class="preview-row"><div><strong>Write evidence</strong><small>audit, tool_call and graph entries</small></div>${chip("allowed")}</div>
    </div>
  `;
}

function mostUsedTools() {
  const items = state.observability?.most_used_tools || [];
  if (!items.length) return `<div class="empty">No persisted tool-call records yet.</div>`;
  return table(["Tool", "Calls"], items.map((item) => [item.tool_name, item.count]));
}

function approvalMix() {
  const approved = state.agents.filter((a) => a.status === "approved").length;
  const pending = state.agents.filter((a) => a.status === "pending").length;
  const revoked = state.agents.filter((a) => a.status === "revoked").length;
  return `<div class="donut-area">
    <div class="donut" style="--a:${Math.min(100, approved * 20 + 1)}%;--b:${Math.min(100, approved * 20 + pending * 20 + 1)}%"><strong>${state.agents.length}</strong></div>
    <div class="legend">
      <span>Approved <b>${approved}</b></span>
      <span>Pending <b>${pending}</b></span>
      <span>Revoked <b>${revoked}</b></span>
    </div>
  </div>`;
}

function decisionDonut() {
  const allowed = state.audit.filter((log) => log.decision === "allowed").length;
  const denied = state.audit.filter((log) => log.decision === "denied").length;
  const pending = state.audit.filter((log) => log.decision === "pending").length;
  const total = Math.max(1, allowed + denied + pending);
  const a = Math.round((allowed / total) * 100);
  const b = Math.round(((allowed + pending) / total) * 100);
  return `<div class="donut-area">
    <div class="donut" style="--a:${a}%;--b:${b}%"><strong>${a}%</strong></div>
    <div class="legend">
      <span>Allowed <b>${allowed}</b></span>
      <span>Pending <b>${pending}</b></span>
      <span>Denied <b>${denied}</b></span>
    </div>
  </div>`;
}

function scopeBars() {
  const scopes = state.overview?.scope_distribution || state.observability?.most_requested_scopes || [];
  if (!scopes.length) return `<div class="empty">No scope data yet.</div>`;
  const max = Math.max(...scopes.map((item) => item.count || 0), 1);
  return `<div class="bar-chart">${scopes.slice(0, 10).map((item) => `
    <div class="bar-group">
      <div class="bars"><div class="bar allowed" style="height:${Math.max(4, ((item.count || 0) / max) * 160)}px"></div></div>
      <div class="bar-label">${escapeHtml(String(item.scope || "").split(":")[0])}</div>
    </div>
  `).join("")}</div>`;
}

function lineChart() {
  const series = state.overview?.activity_series || [];
  if (!series.length) return `<div class="empty">No activity trend available.</div>`;
  const values = series.map((point) => point.allowed + point.denied + point.runtime + point.workflow);
  const max = Math.max(...values, 1);
  const points = values.map((value, index) => {
    const x = 28 + index * (544 / Math.max(1, values.length - 1));
    const y = 180 - (value / max) * 140;
    return `${x},${y}`;
  }).join(" ");
  return `
    <svg class="line-chart" viewBox="0 0 600 220" role="img" aria-label="Activity trend">
      <polygon fill="rgba(35,215,255,0.12)" points="${points} 572,190 28,190"></polygon>
      <polyline fill="none" stroke="#23d7ff" stroke-width="3" points="${points}"></polyline>
      ${values.map((value, index) => {
        const x = 28 + index * (544 / Math.max(1, values.length - 1));
        const y = 180 - (value / max) * 140;
        return `<circle cx="${x}" cy="${y}" r="4" fill="#a5f3fc"><title>${series[index].date}: ${value}</title></circle>`;
      }).join("")}
    </svg>
  `;
}

function auditSignals() {
  return `
    <div class="policy-preview">
      <div class="preview-row"><div><strong>Total audit events</strong><small>registration, approval, token, tools and revocation</small></div><span class="metric-value info">${state.audit.length}</span></div>
      <div class="preview-row"><div><strong>Redacted events</strong><small>events marked PII/secret safe</small></div><span class="metric-value good">${state.audit.filter((log) => log.pii_redacted).length}</span></div>
      <div class="preview-row"><div><strong>Policy failures</strong><small>default-deny or missing-scope decisions</small></div><span class="metric-value bad">${deniedLogs().length}</span></div>
    </div>
  `;
}

function openApiConsole() {
  return `
    <div class="policy-preview">
      <div class="preview-row"><div><strong>Schema</strong><small>FastAPI generated OpenAPI</small></div><a class="ghost-button" href="/openapi.json">JSON</a></div>
      <div class="preview-row"><div><strong>Docs</strong><small>Interactive Swagger console</small></div><a class="ghost-button" href="/docs">Open</a></div>
      <div class="preview-row"><div><strong>Manifest</strong><small>Machine-readable agent auth</small></div><a class="ghost-button" href="/.well-known/agent-auth.json">View</a></div>
    </div>
  `;
}

function primaryFlow() {
  const rows = [
    ["1", "Register agent", "POST /agent-auth/register"],
    ["2", "Approve scopes", "POST /agent-auth/approve/{agent_id}"],
    ["3", "Issue token", "POST /agent-auth/token"],
    ["4", "Call tool", "POST /tools/..."],
    ["5", "Review evidence", "GET /agent-auth/audit"],
  ];
  return table(["Step", "Action", "Endpoint"], rows);
}

function observabilityGrid() {
  const o = state.observability || {};
  return `
    <div class="policy-preview">
      <div class="preview-row"><div><strong>Total Agents</strong><small>registered identities</small></div><span class="metric-value info">${o.total_agents ?? 0}</span></div>
      <div class="preview-row"><div><strong>Allowed Tool Calls</strong><small>policy approved executions</small></div><span class="metric-value good">${o.allowed_tool_calls ?? 0}</span></div>
      <div class="preview-row"><div><strong>Denied Tool Calls</strong><small>blocked by governance</small></div><span class="metric-value bad">${o.denied_tool_calls ?? 0}</span></div>
      <div class="preview-row"><div><strong>High Risk Events</strong><small>audit events with high risk</small></div><span class="metric-value warn">${o.high_risk_events ?? 0}</span></div>
    </div>
  `;
}

function reviewWorkflow() {
  return `
    <div class="policy-preview">
      <div class="preview-row"><div><strong>Capture</strong><small>tool call, required scope and policy reason</small></div>${chip("open")}</div>
      <div class="preview-row"><div><strong>Review</strong><small>operator validates reason and blast radius</small></div>${chip("medium")}</div>
      <div class="preview-row"><div><strong>Mitigate</strong><small>scope, prompt, tool or policy update</small></div>${chip("resolved")}</div>
    </div>
  `;
}

bootstrap().catch((error) => {
  qs("view-grid").innerHTML = panel("Dashboard failed to load", `<p class="panel-subtitle">${escapeHtml(error.message || error)}</p>`, "panel-full");
});
