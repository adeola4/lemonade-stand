// Mission Center page logic — Mission Control theme
const MISSIONS_STORAGE = 'qla_missions';

window.MISSIONS = {
  missions: [],

  init() {
    this.loadData();
    this.bindForms();
    this.render();
  },

  loadData() {
    try { this.missions = JSON.parse(localStorage.getItem(MISSIONS_STORAGE) || '[]'); } catch(e) { this.missions = []; }
  },

  saveData() {
    localStorage.setItem(MISSIONS_STORAGE, JSON.stringify(this.missions));
  },

  bindForms() {
    const input = document.getElementById('quickMissionInput');
    if (input) {
      input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') this.quickAdd();
      });
    }
  },

  quickAdd() {
    const input = document.getElementById('quickMissionInput');
    const prioritySelect = document.getElementById('quickMissionPriority');
    const title = input.value.trim();
    const priority = prioritySelect ? prioritySelect.value : 'standard';

    if (!title) return;

    this.missions.push({
      id: 'm-' + Date.now().toString(36),
      title,
      description: '',
      priority,
      status: 'active',
      company: '',
      pct_complete: 0,
      blockers: '',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      source: 'web'
    });

    this.saveData();
    input.value = '';
    this.render();
  },

  updateStatus(id, status) {
    const m = this.missions.find(x => x.id === id);
    if (m) {
      m.status = status;
      m.updated_at = new Date().toISOString();
      if (status === 'completed') m.pct_complete = 100;
      this.saveData();
      this.render();
    }
  },

  deleteMission(id) {
    this.missions = this.missions.filter(x => x.id !== id);
    this.saveData();
    this.render();
  },

  render() {
    const stats = { total: this.missions.length, active: 0, blocked: 0, completed: 0 };
    this.missions.forEach(m => {
      if (m.status === 'active') stats.active++;
      else if (m.status === 'blocked') stats.blocked++;
      else if (m.status === 'completed') stats.completed++;
    });

    document.getElementById('missionTotal').textContent = stats.total;
    document.getElementById('missionActive').textContent = stats.active;
    document.getElementById('missionBlocked').textContent = stats.blocked;
    document.getElementById('missionCompleted').textContent = stats.completed;

    const list = document.getElementById('missionList');
    if (!this.missions.length) {
      list.innerHTML = '<div class="text-lms-muted text-xs font-medium">NO MISSIONS. ADD ONE ABOVE TO GET STARTED.</div>';
      return;
    }

    const priorityOrder = { critical: 0, standard: 1, routine: 2 };
    this.missions.sort((a, b) => (priorityOrder[a.priority] || 1) - (priorityOrder[b.priority] || 1));

    list.innerHTML = this.missions.map(m => {
      const pColor = { critical: 'text-lms-red', standard: 'text-lms-amber', routine: 'text-lms-green' }[m.priority] || 'text-lms-muted';
      const pLabel = m.priority === 'critical' ? '!' : m.priority === 'routine' ? '•' : '>';
      return `
        <div class="mission-item priority-${m.priority} status-${m.status} px-3 py-2 rounded flex items-center justify-between gap-3">
          <div class="flex items-center gap-3 flex-1 min-w-0">
            <span class="${pColor} font-mono font-bold text-base w-4">${pLabel}</span>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium truncate ${m.status === 'completed' ? 'line-through text-lms-muted' : ''}">${m.title}</div>
              <div class="flex items-center gap-3 text-xs font-medium text-lms-muted mt-0.5">
                <span class="${pColor}">${m.priority.toUpperCase()}</span>
                ${m.company ? `<span>🏢 ${m.company}</span>` : ''}
                <span>${m.pct_complete}%</span>
                <span>${m.created_at ? m.created_at.split('T')[0] : ''}</span>
              </div>
            </div>
          </div>
          <div class="flex gap-1">
            <button onclick="MISSIONS.updateStatus('${m.id}', 'completed')" class="text-xs font-medium px-2 py-1 rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30" title="Complete">✓</button>
            <button onclick="MISSIONS.updateStatus('${m.id}', 'blocked')" class="text-xs font-medium px-2 py-1 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30" title="Block">🛑</button>
            <button onclick="MISSIONS.updateStatus('${m.id}', 'active')" class="text-xs font-medium px-2 py-1 rounded bg-green-500/20 text-green-400 hover:bg-green-500/30" title="Reactivate">▶</button>
            <button onclick="MISSIONS.deleteMission('${m.id}')" class="text-xs font-medium px-2 py-1 rounded bg-white/15 text-gray-200 hover:bg-white/20" title="Delete">✕</button>
          </div>
        </div>
      `;
    }).join('');
  }
};

document.addEventListener('DOMContentLoaded', () => MISSIONS.init());
