(() => {
  const statRow = document.getElementById("statRow");
  const intentBars = document.getElementById("intentBars");
  const intentEmpty = document.getElementById("intentEmpty");
  const logBody = document.getElementById("logBody");

  function statCard(value, label) {
    const div = document.createElement("div");
    div.className = "stat-card";
    div.innerHTML = `<div class="stat-value">${value}</div><div class="stat-label">${label}</div>`;
    return div;
  }

  async function loadMetrics() {
    const res = await fetch("/api/metrics");
    const data = await res.json();

    statRow.innerHTML = "";
    statRow.appendChild(statCard(data.offline_eval.f1_score, "Offline F1-score (holdout)"));
    statRow.appendChild(statCard(data.live.total_interactions, "Live interactions"));
    statRow.appendChild(statCard(`${data.live.avg_latency_ms} ms`, "Avg response latency"));
    statRow.appendChild(statCard(`${(data.live.escalation_rate * 100).toFixed(0)}%`, "Escalated to human"));

    intentBars.innerHTML = "";
    if (data.intent_distribution.length === 0) {
      intentEmpty.hidden = false;
    } else {
      intentEmpty.hidden = true;
      const max = Math.max(...data.intent_distribution.map((d) => d.count));
      data.intent_distribution.forEach((d) => {
        const row = document.createElement("div");
        row.className = "bar-row";
        const pct = Math.max(6, Math.round((d.count / max) * 100));
        row.innerHTML = `
          <div class="bar-label">${d.label}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
          <div class="bar-count">${d.count}</div>
        `;
        intentBars.appendChild(row);
      });
    }
  }

  async function loadLogs() {
    const res = await fetch("/api/logs");
    const rows = await res.json();
    logBody.innerHTML = "";
    rows.forEach((r) => {
      const tr = document.createElement("tr");
      const statusClass = r.escalated ? "status-escalated" : "status-ok";
      const statusText = r.escalated ? "Escalated" : "Resolved";
      tr.innerHTML = `
        <td>${r.timestamp}</td>
        <td>${r.role}</td>
        <td class="message-cell">${r.raw_input_text}</td>
        <td>${r.classified_intent_id ?? "—"}</td>
        <td>${r.confidence_score !== null ? (r.confidence_score * 100).toFixed(0) + "%" : "—"}</td>
        <td>${(r.response_latency_seconds * 1000).toFixed(0)} ms</td>
        <td class="${statusClass}">${statusText}</td>
      `;
      logBody.appendChild(tr);
    });
  }

  loadMetrics();
  loadLogs();
  setInterval(() => {
    loadMetrics();
    loadLogs();
  }, 4000);
})();
