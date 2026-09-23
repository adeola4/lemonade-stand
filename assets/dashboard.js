// Dashboard page logic — Mission Control theme
const STORAGE_KEY = 'qla_pipeline_data';

document.addEventListener('DOMContentLoaded', () => {
  // Quick mission add
  const qm = document.getElementById('quickMissionInput');
  if (qm) {
    qm.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && qm.value.trim()) {
        const missions = JSON.parse(localStorage.getItem('qla_missions') || '[]');
        missions.push({
          id: 'm-' + Date.now().toString(36),
          title: qm.value.trim(),
          description: '',
          priority: 'standard',
          status: 'active',
          company: '',
          pct_complete: 0,
          blockers: '',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          source: 'web'
        });
        localStorage.setItem('qla_missions', JSON.stringify(missions));
        qm.value = '';
        renderDashboardMissions();
      }
    });
  }
  renderDashboardMissions();
});

function renderDashboardMissions() {
  const missions = JSON.parse(localStorage.getItem('qla_missions') || '[]');
  const el = document.getElementById('dashboardMissions');
  const active = missions.filter(m => m.status === 'active').slice(0, 5);
  if (!active.length) {
    el.innerHTML = '<div class="text-lms-muted text-xs font-medium">NO ACTIVE MISSIONS</div>';
    return;
  }
  el.innerHTML = active.map(m => {
    const pColor = { critical: 'text-lms-red', standard: 'text-lms-amber', routine: 'text-lms-green' }[m.priority] || 'text-lms-muted';
    const pLabel = m.priority === 'critical' ? '!' : m.priority === 'routine' ? '•' : '>';
    const editCount = m.edits ? `<span class="font-mono" style="color:#4b5563;font-size:10px">✎${m.edits}</span>` : '';
    return `<div class="mission-item priority-${m.priority} px-2 py-1.5 rounded flex items-center justify-between gap-2">
      <span class="${pColor} font-mono font-bold text-sm font-medium w-3">${pLabel}</span>
      <span class="text-xs font-medium truncate flex-1">${m.title}</span>
      ${editCount}
      <span class="text-xs font-medium ${pColor} font-mono">${m.priority.charAt(0).toUpperCase()}</span>
    </div>`;
  }).join('');
}
