const state = {
  overview: null,
  activity: null,
  audit: [],
  graph: [],
  currentView: "overview",
  search: "",
};

const viewMeta = {
  overview: ["Control Tower", "Overview of governance, runtime operations and intelligence workflows."],
  governance: ["Governance Layer", "Agent identity, scoped credentials, approvals, policy checks and revocation."],
  mcp: ["MCP Security Gateway", "Governed MCP tool invocation, approval routing and redacted tool arguments."],
  automation: ["Automation Control Plane", "Workflow execution decisions, entitlements, approval queues and usage limits."],
  runtime: ["Agent Runtime Control Tower", "Agent runs, runtime state, traces, blocked actions and replay surfaces."],
  incidents: ["LLM Incident Review Console", "Incident queue with severity, evidence context and mitigation workflow."],
  regression: ["Agent Regression Lab", "Scenario registry, regression verdicts and replay previews for agent rollouts."],
  brand: ["Brand Insight Engine", "Governed market signals, competitor analysis and positioning reports."],
  intel: ["Agent Intel MCP", "Repository intelligence, pattern clustering and safe AGENTS.md patch previews."],
  readiness: ["Inference Readiness Advisor", "Inference runtime readiness, hardware fit and deployment recommendations."],
  shared: ["Shared Platform Controls", "Scoped auth, policies, redaction, approvals, audit logs and graph relationships."],
  graph: ["Graph Relationships", "Explainability map across agents, scopes, tools, outputs and audit decisions."],
  audit: ["Audit Logs", "Reviewable event stream for registrations, approvals, tool calls and denied actions."],
};

function qs(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function bootstrap() {
  await refreshData();
  bindEvents();
  setView(location.hash.replace("#", "") || "overview");
}

async function refreshData() {
  const [overview, activity, audit, graph] = await Promise.all([
    loadJson("/platform/overview"),
    loadJson("/platform/activity"),
    loadJson("/agent-auth/audit"),
    loadJson("/graph/edges"),
  ]);
  state.overview = overview;
  state.activity = activity;
  state.audit = audit;
  state.graph = graph;
  renderShell();
}

function bindEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", (event) => {
      const view = event.currentTarget.dataset.view;
      if (view) setView(view);
    });
  });
  document.querySelectorAll("[data-view-jump]").forEach((button) => {
    button.dataset.boundDirectly = "true";
    button.addEventListener("click", (event) => setView(event.currentTarget.dataset.viewJump));
  });
  document.addEventListener("click", (event) => {
    const jump = event.target.closest("[data-view-jump]");
    if (jump && !jump.dataset.boundDirectly) setView(jump.dataset.viewJump);
  });
  qs("refresh-button").addEventListener("click", async () => {
    await refreshData();
    setView(state.currentView);
  });
  qs("global-search").addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    setView(state.currentView, { replaceHash: true });
  });
  qs("drawer-close").addEventListener("click", closeDrawer);
  qs("drawer-backdrop").addEventListener("click", closeDrawer);
}

function setView(view, options = {}) {
  if (!viewMeta[view]) view = "overview";
  state.currentView = view;
  if (!options.replaceHash) location.hash = view;
  document.querySelectorAll("[data-view]").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  const [title, subtitle] = viewMeta[view];
  qs("view-title").textContent = title;
  qs("view-subtitle").textContent = subtitle;
  Promise.resolve(renderMainView(view)).catch((error) => renderViewError(error));
}

function renderViewError(error) {
  qs("view-grid").innerHTML = `
    <section class="panel panel-full">
      <h3>View failed to load</h3>
      <p class="panel-subtitle">${escapeHtml(error.message || error)}</p>
    </section>
  `;
}

function renderShell() {
  renderMetrics(state.overview.metrics);
  renderArchitecture(state.overview.architecture);
}

function renderMetrics(metrics) {
  const cards = [
    ["Total Agents", metrics.total_agents, `${metrics.modules} connected modules`, "metric-good"],
    ["Active Agents", metrics.active_agents, `${metrics.revoked_agents} revoked`, "metric-good"],
    ["Incidents 7d", metrics.incidents_7d, "runtime and policy signals", metrics.incidents_7d ? "metric-bad" : "metric-good"],
    ["Policy Violations", metrics.policy_violations, `${metrics.denied_tool_calls} denied calls`, metrics.policy_violations ? "metric-warn" : "metric-good"],
    ["Approvals Pending", metrics.pending_approvals, "awaiting human review", metrics.pending_approvals ? "metric-warn" : "metric-good"],
    ["Runtime Health", `${metrics.runtime_health}%`, `${metrics.graph_edges} graph edges`, "metric-good"],
  ];
  qs("metric-grid").innerHTML = cards.map(([label, value, foot, klass]) => `
    <article class="metric-card">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value ${klass}">${escapeHtml(value)}</div>
      <div class="metric-foot">${escapeHtml(foot)}</div>
    </article>
  `).join("");
}

function renderArchitecture(groups) {
  qs("architecture-flow").innerHTML = groups.map((group) => `
    <article class="layer-card ${group.color}">
      <h3>${escapeHtml(group.layer)}</h3>
      <ul>
        ${group.modules.map((module) => `
          <li>
            <button class="plain-link" type="button" data-module="${escapeHtml(module.key || module.name)}">
              ${escapeHtml(module.name)}
            </button>
          </li>
        `).join("")}
      </ul>
      <div class="layer-visual" aria-hidden="true"></div>
    </article>
  `).join("");
  document.querySelectorAll("[data-module]").forEach((button) => {
    button.addEventListener("click", () => openModuleDrawer(button.dataset.module));
  });
}

function renderMainView(view) {
  if (view === "overview") return renderOverview();
  if (view === "governance") return renderLayer("governance");
  if (view === "mcp") return renderMcp();
  if (view === "automation") return renderAutomation();
  if (view === "runtime") return renderRuntime();
  if (view === "incidents") return renderIncidents();
  if (view === "regression") return renderRegression();
  if (view === "brand") return renderBrand();
  if (view === "intel") return renderIntelligence();
  if (view === "readiness") return renderReadiness();
  if (view === "shared") return renderShared();
  if (view === "graph") return renderGraph();
  if (view === "audit") return renderAudit();
}

function renderOverview() {
  const overview = state.overview;
  qs("view-grid").innerHTML = `
    ${renderActivityPanel()}
    ${renderLinePanel("Agent Activity Overview", overview.activity_series)}
    ${renderTopAgentsPanel(overview.top_agents)}
    ${renderCompliancePanel(overview.compliance)}
    ${renderApprovalsPanel()}
    ${renderRuntimePerformancePanel()}
    ${renderIntelligenceInsightsPanel()}
  `;
}

function filterRows(rows, fields) {
  if (!state.search) return rows;
  return rows.filter((row) => fields.some((field) => String(row[field] ?? "").toLowerCase().includes(state.search)));
}

function renderActivityPanel() {
  const rows = filterRows(state.activity.items.slice(0, 8), ["title", "module", "reason", "decision"]);
  return `
    <section class="panel">
      <h3>Recent Incidents & Decisions</h3>
      <p class="panel-subtitle">Backend events, not static dashboard placeholders.</p>
      <div class="list">
        ${rows.map((item) => `
          <div class="list-row">
            <div>
              <div class="row-title">${escapeHtml(item.title)}</div>
              <div class="row-meta">${escapeHtml(item.module)} - ${escapeHtml(item.reason)}</div>
            </div>
            <span class="pill ${escapeHtml(item.decision)}">${escapeHtml(item.decision)}</span>
          </div>
        `).join("") || emptyState("No activity matches the current search.")}
      </div>
    </section>
  `;
}

function renderLinePanel(title, series) {
  const values = series.map((point) => point.allowed + point.denied + point.runtime + point.workflow);
  const max = Math.max(...values, 1);
  const points = values.map((value, index) => {
    const x = 28 + index * (544 / Math.max(1, values.length - 1));
    const y = 170 - (value / max) * 130;
    return `${x},${y}`;
  }).join(" ");
  return `
    <section class="panel panel-wide chart-card">
      <div class="section-heading">
        <div>
          <h3>${escapeHtml(title)}</h3>
          <p>Computed from audit logs, runtime runs and workflow execution data.</p>
        </div>
      </div>
      <svg class="line-chart" viewBox="0 0 600 205" role="img" aria-label="${escapeHtml(title)}">
        <polyline fill="none" stroke="#9b5cff" stroke-width="3" points="${points}" />
        <polygon fill="rgba(155,92,255,0.16)" points="${points} 572,180 28,180" />
        ${values.map((value, index) => {
          const x = 28 + index * (544 / Math.max(1, values.length - 1));
          const y = 170 - (value / max) * 130;
          return `<circle cx="${x}" cy="${y}" r="4" fill="#d7c8ff"><title>${series[index].date}: ${value}</title></circle>`;
        }).join("")}
      </svg>
    </section>
  `;
}

function renderTopAgentsPanel(rows) {
  return `
    <section class="panel">
      <h3>Top Agents by Activity</h3>
      <p class="panel-subtitle">Derived from audit owner activity and runtime runs.</p>
      <div class="list">
        ${rows.map((row) => `
          <div class="list-row">
            <div>
              <div class="row-title">${escapeHtml(row.name)}</div>
              <div class="row-meta">${escapeHtml(row.actions)} actions</div>
            </div>
            <span class="${row.trend >= 0 ? "metric-good" : "metric-bad"}">${row.trend >= 0 ? "up" : "down"} ${Math.abs(row.trend)}%</span>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

function renderCompliancePanel(compliance) {
  const compliant = Math.min(100, compliance.compliant);
  const warnings = Math.min(100, compliant + compliance.warnings);
  return `
    <section class="panel">
      <h3>Policy Compliance</h3>
      <p class="panel-subtitle">Calculated from allowed, denied and incident counts.</p>
      <div class="donut-wrap">
        <div class="donut" style="--compliant:${compliant}%;--warnings:${warnings}%"><strong>${compliant}%</strong></div>
        <div class="legend">
          <span>Compliant <b>${compliance.compliant}%</b></span>
          <span>Warnings <b>${compliance.warnings}%</b></span>
          <span>Violations <b>${compliance.violations}%</b></span>
        </div>
      </div>
    </section>
  `;
}

function renderApprovalsPanel() {
  const pending = state.overview.metrics.pending_approvals;
  const rows = [
    ["Tool Permission Request", "Agent: Content Analysis Agent", pending ? "pending" : "stable"],
    ["Data Access Request", "Agent: Brand Insight Agent", "approval_required"],
    ["Policy Exception Request", "Agent: Research Agent", "pending"],
  ];
  return simpleListPanel("Approvals Queue", rows);
}

function renderRuntimePerformancePanel() {
  const metrics = state.overview.metrics;
  return `
    <section class="panel">
      <h3>Runtime Performance</h3>
      <p class="panel-subtitle">Summary of runtime and graph state.</p>
      <div class="module-grid" style="grid-template-columns: repeat(3, 1fr); margin-top: 14px;">
        ${smallStat("Health", `${metrics.runtime_health}%`, "metric-good")}
        ${smallStat("Activity", metrics.total_activity, "metric-good")}
        ${smallStat("Graph Edges", metrics.graph_edges, "metric-good")}
      </div>
      <button class="card-button" type="button" data-view-jump="runtime" style="margin-top:14px;">View runtime</button>
    </section>
  `;
}

function renderIntelligenceInsightsPanel() {
  const items = [
    ["Brand sentiment improved", "Brand Insight Engine", "operational"],
    ["Reusable agent patterns clustered", "Agent Intel MCP", "operational"],
    ["Inference readiness score available", "Inference Readiness Advisor", "operational"],
  ];
  return simpleListPanel("Intelligence Insights", items);
}

function smallStat(label, value, klass) {
  return `<div class="metric-card" style="min-height:100px;"><div class="metric-label">${escapeHtml(label)}</div><div class="metric-value ${klass}">${escapeHtml(value)}</div></div>`;
}

function simpleListPanel(title, rows) {
  return `
    <section class="panel">
      <h3>${escapeHtml(title)}</h3>
      <div class="list">
        ${rows.map(([name, meta, status]) => `
          <div class="list-row">
            <div><div class="row-title">${escapeHtml(name)}</div><div class="row-meta">${escapeHtml(meta)}</div></div>
            <span class="pill ${escapeHtml(status)}">${escapeHtml(status)}</span>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

async function renderLayer(layerKey) {
  const detail = await loadJson(`/platform/layers/${layerKey}`);
  qs("view-grid").innerHTML = `
    <section class="panel panel-full">
      <h3>${escapeHtml(detail.layer)}</h3>
      <p class="panel-subtitle">Connected modules in this layer.</p>
      <div class="module-grid" style="margin-top: 14px;">
        ${detail.modules.map(renderModuleCard).join("")}
      </div>
    </section>
    ${renderScopePanel()}
    ${renderAuditSummaryPanel()}
  `;
  bindModuleCards();
}

function renderModuleCard(module) {
  return `
    <article class="module-card" data-module-card="${escapeHtml(module.key || module.name)}">
      <span class="pill ${escapeHtml(module.status || "operational")}">${escapeHtml(module.status || "active")}</span>
      <h3 style="margin-top:12px;">${escapeHtml(module.name)}</h3>
      <p>${escapeHtml(module.summary)}</p>
      <div class="capabilities">${(module.capabilities || []).map((cap) => `<span>${escapeHtml(cap)}</span>`).join("")}</div>
    </article>
  `;
}

function bindModuleCards() {
  document.querySelectorAll("[data-module-card]").forEach((card) => card.addEventListener("click", () => openModuleDrawer(card.dataset.moduleCard)));
}

function renderScopePanel() {
  const items = state.overview.scope_distribution;
  const max = Math.max(...items.map((item) => item.count), 1);
  return `
    <section class="panel">
      <h3>Scope Coverage</h3>
      <p class="panel-subtitle">Actual approved/requested scope counts from registered agents.</p>
      <div class="bar-chart">
        ${items.map((item) => `
          <div class="bar-pair">
            <div class="bars"><div class="bar allowed" style="height:${(item.count / max) * 160 + 3}px"></div></div>
            <div class="bar-label">${escapeHtml(item.scope.split(":")[0])}</div>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

function renderAuditSummaryPanel() {
  const allowed = state.audit.filter((log) => log.decision === "allowed").length;
  const denied = state.audit.filter((log) => log.decision === "denied").length;
  const pending = state.audit.filter((log) => log.decision === "pending").length;
  return `
    <section class="panel">
      <h3>Audit Decision Mix</h3>
      <p class="panel-subtitle">Decision counts from <code>/agent-auth/audit</code>.</p>
      <div class="module-grid" style="grid-template-columns: repeat(3, 1fr); margin-top: 14px;">
        ${smallStat("Allowed", allowed, "metric-good")}
        ${smallStat("Denied", denied, "metric-bad")}
        ${smallStat("Pending", pending, "metric-warn")}
      </div>
    </section>
  `;
}

function renderModuleFocus(key, extraPanel) {
  const module = state.overview.modules.find((item) => item.key === key);
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide">
      <h3>${escapeHtml(module.name)}</h3>
      <p class="panel-subtitle">${escapeHtml(module.summary)}</p>
      <div class="module-grid" style="margin-top: 14px;">
        ${smallStat("Health", `${module.health}%`, module.health >= 95 ? "metric-good" : "metric-warn")}
        ${smallStat("Status", module.status, module.status === "operational" ? "metric-good" : "metric-warn")}
        ${smallStat("Capabilities", module.capabilities.length, "metric-good")}
      </div>
      <div class="capabilities">${module.capabilities.map((cap) => `<span>${escapeHtml(cap)}</span>`).join("")}</div>
    </section>
    ${extraPanel}
    ${renderAuditSummaryPanel()}
  `;
}

function renderMcp() {
  const mcpLogs = state.audit.filter((log) => (log.tool_name || "").startsWith("mcp."));
  const mcpModule = state.overview.modules.find((item) => item.key === "mcp-security-gateway");
  const mcpEdges = state.graph.filter((edge) => (edge.source_type || "").includes("mcp") || (edge.target_type || "").includes("mcp") || (edge.relationship || "").includes("mcp"));
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide module-hero mcp-hero">
      <div>
        <span class="hero-kicker">Security boundary</span>
        <h3>${escapeHtml(mcpModule.name)}</h3>
        <p class="panel-subtitle">${escapeHtml(mcpModule.summary)}</p>
      </div>
      <div class="security-flow" aria-label="MCP security flow">
        <span>Agent</span>
        <b>Policy Check</b>
        <b>Scope Match</b>
        <b>Secret Redaction</b>
        <span>Tool Result</span>
      </div>
      <div class="module-grid" style="margin-top: 16px;">
        ${smallStat("Required Scope", "mcp:tool:invoke", "metric-warn")}
        ${smallStat("MCP Decisions", mcpLogs.length, "metric-good")}
        ${smallStat("Graph Edges", mcpEdges.length, "metric-good")}
      </div>
      <div class="capabilities">${mcpModule.capabilities.map((cap) => `<span>${escapeHtml(cap)}</span>`).join("")}</div>
    </section>
    <section class="panel">
      <h3>MCP Decisions</h3>
      <p class="panel-subtitle">Tool calls that crossed the MCP policy boundary.</p>
      <div class="list">${mcpLogs.map(auditRow).join("") || emptyState("No MCP calls yet. Use /tools/mcp/invoke_tool to create governed requests.")}</div>
    </section>
    <section class="panel">
      <h3>Security Controls</h3>
      <div class="control-stack">
        <div><strong>Default deny</strong><span>Unknown tools are denied before execution.</span></div>
        <div><strong>Scoped invocation</strong><span>Token must contain the MCP tool scope.</span></div>
        <div><strong>Secret masking</strong><span>API keys and sensitive arguments are redacted.</span></div>
        <div><strong>Audit edge</strong><span>Each decision is written into audit and graph data.</span></div>
      </div>
    </section>
  `;
}

async function renderBrand() {
  const detail = await loadJson("/platform/intelligence");
  const brandModule = state.overview.modules.find((item) => item.key === "brand-insight-engine");
  const brandLogs = state.audit.filter((log) => (log.tool_name || "").startsWith("brand."));
  const brandSignals = detail.signals.filter((signal) => signal.module === "brand-insight-engine");
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide module-hero brand-hero">
      <div>
        <span class="hero-kicker">Market intelligence</span>
        <h3>${escapeHtml(brandModule.name)}</h3>
        <p class="panel-subtitle">${escapeHtml(brandModule.summary)}</p>
      </div>
      <div class="insight-strip">
        ${brandSignals.map((signal) => `
          <div>
            <strong>${escapeHtml(signal.value)}${escapeHtml(signal.unit)}</strong>
            <span>${escapeHtml(signal.title)}</span>
          </div>
        `).join("") || `<div><strong>0</strong><span>No brand signals yet</span></div>`}
      </div>
      <div class="capabilities">${brandModule.capabilities.map((cap) => `<span>${escapeHtml(cap)}</span>`).join("")}</div>
    </section>
    <section class="panel">
      <h3>Brand Insight Decisions</h3>
      <p class="panel-subtitle">Governed insight tool calls and report decisions.</p>
      <div class="list">${brandLogs.map(auditRow).join("") || emptyState("No Brand Insight calls yet. Use /tools/brand/analyze_market_signals.")}</div>
    </section>
    <section class="panel">
      <h3>Review Queue</h3>
      <div class="control-stack">
        <div><strong>Signal extraction</strong><span>Marketing and competitor signals become structured findings.</span></div>
        <div><strong>Human review</strong><span>Reports that create outward-facing positioning require review.</span></div>
        <div><strong>Governed output</strong><span>Every insight keeps scope, tenant and audit context.</span></div>
      </div>
    </section>
  `;
}

async function renderAutomation() {
  const detail = await loadJson("/platform/automation");
  const automationModule = state.overview.modules.find((item) => item.key === "automation-control-plane");
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide module-hero automation-hero">
      <div>
        <span class="hero-kicker">Workflow control plane</span>
        <h3>${escapeHtml(automationModule.name)}</h3>
        <p class="panel-subtitle">${escapeHtml(automationModule.summary)}</p>
      </div>
      <div class="workflow-lanes" aria-label="Automation decision lanes">
        <div><strong>Allowed</strong><span>${escapeHtml(detail.metrics.allowed)}</span></div>
        <div><strong>Approval Queue</strong><span>${escapeHtml(detail.metrics.approval_required)}</span></div>
        <div><strong>Denied</strong><span>${escapeHtml(detail.metrics.denied)}</span></div>
      </div>
      <div class="capabilities">${automationModule.capabilities.map((cap) => `<span>${escapeHtml(cap)}</span>`).join("")}</div>
    </section>
    <section class="panel panel-wide">
      <h3>Workflow Execution Decisions</h3>
      <p class="panel-subtitle">Execution counts from Automation Control Plane data.</p>
      ${table(["Workflow", "Decision", "Count"], detail.executions.map((row) => [row.workflow, row.decision, row.count]))}
    </section>
    <section class="panel">
      <h3>Approval Routing</h3>
      <div class="control-stack">
        <div><strong>Plan check</strong><span>Workflow is checked against tenant entitlement.</span></div>
        <div><strong>Risk routing</strong><span>Sensitive workflow moves to approval queue.</span></div>
        <div><strong>Execution log</strong><span>Decision is persisted for operator review.</span></div>
      </div>
    </section>
  `;
}

async function renderRuntime() {
  const detail = await loadJson("/platform/runtime");
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide">
      <h3>Runtime Runs</h3>
      <p class="panel-subtitle">Runtime state derived from Agent Runtime Control Tower domain data.</p>
      ${table(["Agent", "Status", "Latency", "Tool Calls", "Cost"], detail.runs.map((row) => [row.agent, row.status, `${row.latency_ms}ms`, row.tool_calls, `$${row.cost_usd}`]))}
    </section>
    <section class="panel">
      <h3>Runtime Summary</h3>
      <div class="module-grid" style="grid-template-columns: 1fr; margin-top:14px;">
        ${smallStat("Completed", detail.metrics.completed, "metric-good")}
        ${smallStat("Blocked", detail.metrics.blocked, "metric-bad")}
        ${smallStat("Avg Latency", `${detail.metrics.avg_latency_ms}ms`, "metric-warn")}
      </div>
    </section>
  `;
}

async function renderIncidents() {
  const detail = await loadJson("/platform/incidents");
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide module-hero incident-hero">
      <div>
        <span class="hero-kicker">Incident review</span>
        <h3>LLM Incident Review Console</h3>
        <p class="panel-subtitle">Evidence, severity and mitigation tracking for failed or risky agent behavior.</p>
      </div>
      <div class="module-grid" style="margin-top: 16px;">
        ${smallStat("High", detail.metrics.high || 0, "metric-bad")}
        ${smallStat("Medium", detail.metrics.medium || 0, "metric-warn")}
        ${smallStat("Low", detail.metrics.low || 0, "metric-good")}
      </div>
    </section>
    <section class="panel panel-wide">
      <h3>Incident Queue</h3>
      ${table(["Incident", "Severity", "Module", "Age"], detail.incidents.map((row) => [row.title, row.severity, row.module, row.age]))}
    </section>
    <section class="panel">
      <h3>Review Workflow</h3>
      <div class="control-stack">
        <div><strong>Evidence</strong><span>Capture tool call, scope, decision and affected module.</span></div>
        <div><strong>Replay preview</strong><span>Operator can reproduce the failure path safely.</span></div>
        <div><strong>Mitigation</strong><span>Policy or regression scenario is updated before rollout.</span></div>
      </div>
    </section>
    ${renderAuditSummaryPanel()}
  `;
}

async function renderRegression() {
  const detail = await loadJson("/platform/regression");
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide">
      <h3>Regression Runs</h3>
      ${table(["Scenario", "Baseline", "Candidate", "Verdict", "Latency Delta"], detail.runs.map((row) => [row.scenario, row.baseline, row.candidate, row.verdict, `${row.latency_delta}%`]))}
    </section>
    <section class="panel">
      <h3>Release Guardrail</h3>
      <p class="panel-subtitle">Regressions should block rollout until reviewed.</p>
      <div class="module-grid" style="grid-template-columns: 1fr; margin-top:14px;">
        ${smallStat("Stable", detail.metrics.stable || 0, "metric-good")}
        ${smallStat("Regressions", detail.metrics.regression || 0, "metric-bad")}
      </div>
    </section>
  `;
}

async function renderIntelligence() {
  const detail = await loadJson("/platform/intelligence");
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide">
      <h3>Intelligence Signals</h3>
      ${table(["Signal", "Value", "Module"], detail.signals.map((row) => [row.title, `${row.value}${row.unit}`, row.module]))}
    </section>
    ${renderLayerCardOnly("Intelligence Layer")}
  `;
  bindModuleCards();
}

async function renderReadiness() {
  const detail = await loadJson("/platform/readiness");
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide">
      <h3>Inference Readiness</h3>
      ${table(["Profile", "Score", "Runtime", "Recommendation"], detail.assessments.map((row) => [row.profile, `${row.score}/100`, row.runtime, row.recommendation]))}
    </section>
    <section class="panel">
      <h3>Average Readiness</h3>
      ${smallStat("Score", `${detail.metrics.average_score}/100`, "metric-good")}
    </section>
  `;
}

function renderLayerCardOnly(layer) {
  const modules = state.overview.modules.filter((module) => module.layer === layer);
  return `<section class="panel">${modules.map(renderModuleCard).join("")}</section>`;
}

function renderShared() {
  const metrics = state.overview.metrics;
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide module-hero shared-hero">
      <div>
        <span class="hero-kicker">Shared platform layer</span>
        <h3>Shared Controls</h3>
        <p class="panel-subtitle">Common auth, policy, redaction, audit and graph primitives used by every module.</p>
      </div>
      <div class="module-grid" style="margin-top: 16px;">
        ${smallStat("Audit Events", state.audit.length, "metric-good")}
        ${smallStat("Graph Edges", state.graph.length, "metric-good")}
        ${smallStat("Scopes", state.overview.scope_distribution.length, "metric-warn")}
      </div>
    </section>
    <section class="panel">
      <h3>Control Primitives</h3>
      <div class="control-stack">
        <div><strong>Scoped Auth</strong><span>Short-lived JWTs and approved scope sets.</span></div>
        <div><strong>Policy Engine</strong><span>Default-deny tool to scope enforcement.</span></div>
        <div><strong>PII / Secret Redaction</strong><span>Sensitive fields are masked before responses and logs.</span></div>
        <div><strong>Graph Relationships</strong><span>Explainable edges across agents, tools, scopes and outputs.</span></div>
      </div>
    </section>
    ${renderScopePanel()}
    ${renderAuditSummaryPanel()}
  `;
}

function renderGraph() {
  const rows = filterRows(state.graph, ["source_type", "source_id", "relation", "target_type", "target_id", "tenant_id"]);
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide module-hero graph-hero">
      <div>
        <span class="hero-kicker">Explainability map</span>
        <h3>Graph Relationships</h3>
        <p class="panel-subtitle">Trace how agents, scopes, tools and outputs connect after governed execution.</p>
      </div>
      <div class="module-grid" style="margin-top: 16px;">
        ${smallStat("Edges", rows.length, "metric-good")}
        ${smallStat("Tenants", new Set(rows.map((edge) => edge.tenant_id)).size, "metric-good")}
        ${smallStat("Relations", new Set(rows.map((edge) => edge.relation)).size, "metric-warn")}
      </div>
    </section>
    <section class="panel panel-full">
      <h3>Relationship Graph</h3>
      <p class="panel-subtitle">Edges written by governed tool calls. These are queryable through <code>/graph/edges</code>.</p>
      ${table(["Source", "Relation", "Target", "Tenant"], rows.map((edge) => [`${edge.source_type}:${edge.source_id}`, edge.relation, `${edge.target_type}:${edge.target_id}`, edge.tenant_id]))}
    </section>
  `;
}

function renderAudit() {
  const rows = filterRows(state.audit, ["action", "tool_name", "decision", "reason", "owner_user_id", "requested_scope"]);
  const allowed = rows.filter((log) => log.decision === "allowed").length;
  const denied = rows.filter((log) => log.decision === "denied").length;
  const pending = rows.filter((log) => log.decision === "pending").length;
  qs("view-grid").innerHTML = `
    <section class="panel panel-wide module-hero audit-hero">
      <div>
        <span class="hero-kicker">Audit evidence</span>
        <h3>Audit Logs</h3>
        <p class="panel-subtitle">Decision trail for registrations, approvals, token issuance, revocation and tool calls.</p>
      </div>
      <div class="module-grid" style="margin-top: 16px;">
        ${smallStat("Allowed", allowed, "metric-good")}
        ${smallStat("Denied", denied, "metric-bad")}
        ${smallStat("Pending", pending, "metric-warn")}
      </div>
    </section>
    <section class="panel panel-full">
      <h3>Audit Logs</h3>
      <p class="panel-subtitle">Live data from <code>/agent-auth/audit</code>.</p>
      ${table(["Action", "Tool", "Scope", "Decision", "Reason"], rows.map((log) => [log.action, log.tool_name || "agent-auth", log.requested_scope || "n/a", log.decision, log.reason]))}
    </section>
  `;
}

function auditRow(log) {
  return `
    <div class="list-row">
      <div><div class="row-title">${escapeHtml(log.action)}</div><div class="row-meta">${escapeHtml(log.tool_name || "agent-auth")} - ${escapeHtml(log.reason)}</div></div>
      <span class="pill ${escapeHtml(log.decision)}">${escapeHtml(log.decision)}</span>
    </div>
  `;
}

function table(headers, rows) {
  const filtered = state.search ? rows.filter((row) => row.some((cell) => String(cell).toLowerCase().includes(state.search))) : rows;
  if (!filtered.length) return emptyState("No rows match the current search.");
  return `
    <table class="table">
      <thead><tr>${headers.map((head) => `<th>${escapeHtml(head)}</th>`).join("")}</tr></thead>
      <tbody>
        ${filtered.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}
      </tbody>
    </table>
  `;
}

function emptyState(message) {
  return `<div class="empty">${escapeHtml(message)}</div>`;
}

function openModuleDrawer(key) {
  const module = state.overview.modules.find((item) => item.key === key || item.name === key);
  if (!module) return;
  qs("drawer-eyebrow").textContent = module.layer;
  qs("drawer-title").textContent = module.name;
  qs("drawer-body").innerHTML = `
    <p>${escapeHtml(module.summary)}</p>
    <div class="module-grid" style="grid-template-columns: repeat(2, 1fr); margin-top: 16px;">
      ${smallStat("Health", `${module.health}%`, module.health >= 95 ? "metric-good" : "metric-warn")}
      ${smallStat("Status", module.status, module.status === "operational" ? "metric-good" : "metric-warn")}
    </div>
    <h3 style="margin-top:18px;">Capabilities</h3>
    <div class="capabilities">${module.capabilities.map((cap) => `<span>${escapeHtml(cap)}</span>`).join("")}</div>
    <p style="margin-top:18px;">API route: <code>${escapeHtml(module.route)}</code></p>
  `;
  qs("drawer-backdrop").classList.remove("hidden");
  qs("drawer").classList.remove("hidden");
  qs("drawer").setAttribute("aria-hidden", "false");
}

function closeDrawer() {
  qs("drawer-backdrop").classList.add("hidden");
  qs("drawer").classList.add("hidden");
  qs("drawer").setAttribute("aria-hidden", "true");
}

window.addEventListener("hashchange", () => setView(location.hash.replace("#", "") || "overview", { replaceHash: true }));
bootstrap().catch((error) => {
  renderViewError(error);
});
