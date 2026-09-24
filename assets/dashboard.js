// Dashboard page logic — Mission Control theme
// ALL data fetched from /api/data (Google Sheets backend) — no localStorage

const API = 'http://129.213.81.33:8645/data';
const API_KEY = 'lms-default-key-2026';

async function apiGet(sheet) {
  const res = await fetch(`${API}/${encodeURIComponent(sheet)}`, {
    headers: { 'X-API-Key': API_KEY }
  });
  const json = await res.json();
  return json.data || [];
}

async function apiPost(sheet, action, payload = {}) {
  const res = await fetch(`${API}/${encodeURIComponent(sheet)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
    body: JSON.stringify({ action, ...payload })
  });
  const json = await res.json();
  return json;
}

document.addEventListener('DOMContentLoaded', () => {
  // Quick mission add
  const qm = document.getElementById('quickMissionInput');
  if (qm) {
    qm.addEventListener('keypress', async (e) => {
      if (e.key === 'Enter' && qm.value.trim()) {
        await apiPost('Missions', 'create', {
          row: {
            id: 'm-' + Date.now().toString(36),
            name: qm.value.trim(),
            rank: 'B',
            description: '',
            company: '',
            assigned_to: '',
            status: 'active',
            acceptance: 'pending',
            progress: 'not_started',
            notes: '',
            edits: 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            source: 'web'
          }
        });
        qm.value = '';
        renderDashboardMissions();
        renderDashboardMetrics();
      }
    });
  }
  renderDashboardMissions();
  renderDashboardMetrics();
  // Keep metrics live — recompute every 30s
  setInterval(renderDashboardMetrics, 30000);
});

// ===== LIVE METRICS =====
async function getMissions() { return apiGet('Missions'); }
async function getV0Loops() { return apiGet('Loops'); }
async function getV1Loops() { return apiGet('V1Loops'); }
async function getPipeline() { return apiGet('Pipeline'); }

async function renderDashboardMetrics() {
  // --- Missions stat pill ---
  const missions = await getMissions();
  const activeMissions = missions.filter(m => m.status === 'active');
  const missionsEl = document.getElementById('statMissions');
  if (missionsEl) missionsEl.textContent = activeMissions.length + ' Missions';

  // --- Loops stat pill (V0 running + V1 executing/running) ---
  const v0 = await getV0Loops();
  const v1 = await getV1Loops();
  const runningLoops =
    v0.filter(l => l.status === 'running').length +
    v1.filter(l => l.state === 'running' || l.state === 'executing').length;
  const loopsEl = document.getElementById('statLoops');
  if (loopsEl) loopsEl.textContent = runningLoops + ' Loops';

  // --- Deals stat pill (from pipeline data) ---
  const pipeline = await getPipeline();
  let dealCount = 0;
  pipeline.forEach(c => { dealCount += (c.deals || []).length; });
  const dealsEl = document.getElementById('statDeals');
  if (dealsEl) dealsEl.textContent = dealCount + ' Deals';

  // --- Active Loops panel ---
  const loopsPanel = document.getElementById('activeLoops');
  if (loopsPanel) {
    const allRunning = [
      ...v0.filter(l => l.status === 'running').map(l => ({ name: l.name || l.goal || 'Loop', state: 'running', kind: 'V0' })),
      ...v1.filter(l => l.state === 'running' || l.state === 'executing').map(l => ({ name: l.goal || l.name || 'Loop', state: l.state, kind: 'V1' }))
    ];
    loopsPanel.innerHTML = allRunning.length === 0
      ? '<div class="text-sm text-center py-4" style="color: #6b7280">No active loops</div>'
      : allRunning.slice(0, 6).map(l => `
          <div class="flex items-center justify-between gap-2">
            <span class="text-xs truncate flex-1" style="color:#d1d5db">${l.name}</span>
            <span class="pill pill-active">${l.kind} · ${l.state}</span>
          </div>
        `).join('');
  }

  // --- Pipeline panel (Sourced / Approaching / Closing) ---
  const stageOf = d => d.stage || d.status || 'sourced';
  let sourced = 0, approaching = 0, closing = 0;
  pipeline.forEach(c => {
    (c.deals || []).forEach(d => {
      const s = stageOf(d);
      if (['completed', 'killed', 'on_hold'].includes(s)) return;
      if (['sourced', 'identified', 'scanning'].includes(s)) sourced++;
      else if (['approaching', 'contacted', 'outreach', 'negotiation', 'loi'].includes(s)) approaching++;
      else if (['closing', 'due_diligence', 'signing', 'final'].includes(s)) closing++;
      else sourced++;
    });
  });
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('pipeSourced', sourced);
  set('pipeApproaching', approaching);
  set('pipeClosing', closing);
}

async function renderDashboardMissions() {
  const missions = await getMissions();
  const el = document.getElementById('dashboardMissions');
  const active = missions.filter(m => m.status === 'active').slice(0, 5);
  if (!active.length) {
    el.innerHTML = '<div class="text-lms-muted text-xs font-medium">NO ACTIVE MISSIONS</div>';
    return;
  }
  el.innerHTML = active.map(m => {
    const priority = m.priority || { S: 'critical', A: 'critical', B: 'standard', C: 'routine', D: 'routine' }[m.rank] || 'standard';
    const pColor = { critical: 'text-lms-red', standard: 'text-lms-amber', routine: 'text-lms-green' }[priority] || 'text-lms-muted';
    const pLabel = priority === 'critical' ? '!' : priority === 'routine' ? '•' : '>';
    const editCount = m.edits ? `<span class="font-mono" style="color:#4b5563;font-size:10px">✎${m.edits}</span>` : '';
    const noteAlert = (m.notes || []).filter(n => !n.acknowledged).length > 0
      ? `<span style="color:#fbbf24;font-size:10px">🔔</span>` : '';
    const progressDot = m.progress === 'in_progress' ? '🟡' : m.progress === 'complete' ? '🟢' : m.acceptance === 'declined' ? '🔴' : m.acceptance === 'accepted' ? '⚪' : '🔵';
    return `<div class="mission-item priority-${priority} px-2 py-1.5 rounded flex items-center justify-between gap-2">
      <span class="${pColor} font-mono font-bold text-sm font-medium w-3">${pLabel}</span>
      <span class="text-xs font-medium truncate flex-1">${m.name || m.title}</span>
      ${noteAlert}
      ${editCount}
      <span class="text-xs">${progressDot}</span>
      <span class="text-xs font-medium ${pColor} font-mono">${priority.charAt(0).toUpperCase()}</span>
    </div>`;
  }).join('');
}
