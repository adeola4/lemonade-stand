// Deal Generation page logic
const STORAGE_KEY = 'qla_pipeline_data';

window.DEALS = {
  companies: [],
  selectedApproach: null,

  init() {
    this.loadData();
    this.bindForms();
    this.renderPipeline();
  },

  loadData() {
    try { this.companies = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch(e) { this.companies = []; }
  },

  saveData() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this.companies));
  },

  showTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.getElementById('tab' + tab.charAt(0).toUpperCase() + tab.slice(1)).classList.remove('hidden');
  },

  bindForms() {
    // Launch form
    const launchForm = document.getElementById('launchForm');
    if (launchForm) {
      launchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.generateDealCard();
      });
    }

    // Approach form
    const approachForm = document.getElementById('approachForm');
    if (approachForm) {
      approachForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.generateApproaches();
      });
    }

    // QLA form
    const qlaForm = document.getElementById('qlaForm');
    if (qlaForm) {
      qlaForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.startQLA();
      });
    }
  },

  generateDealCard() {
    const idea = document.getElementById('launchIdea').value.trim();
    const company = document.getElementById('launchCompany').value.trim() || 'New Venture';
    const vertical = document.getElementById('launchVertical').value.trim() || 'TBD';
    const geo = document.getElementById('launchGeo').value.trim() || 'TBD';
    const approach = document.getElementById('launchApproach').value;

    if (!idea) return;

    const threadName = `${company} — ${idea.substring(0, 50)}${idea.length > 50 ? '...' : ''} (${approach})`;

    const dealCard = `🍋 **LEMONADE STAND — NEW DEAL THREAD**

**Company:** ${company}
**Deal:** ${idea}
**Approach:** ${approach}
**Vertical:** ${vertical}
**Geography:** ${geo}

---

**QLA Knowledge Base methodology will execute here.**

Use this thread to:
• Track deal progress step-by-step
• Store documents, LOIs, research
• Coordinate outreach and follow-ups
• Update pipeline status

**NEXT STEPS:**
1. Create Discord thread with name: "${threadName}"
2. Paste this deal card as the first message
3. Run QLA process to source targets and generate documents`;

    document.getElementById('launchDealCard').textContent = dealCard;
    document.getElementById('launchOutput').classList.remove('hidden');
  },

  copyLaunch() {
    const text = document.getElementById('launchDealCard').textContent;
    navigator.clipboard.writeText(text).then(() => alert('Copied to clipboard!'));
  },

  generateApproaches() {
    const idea = document.getElementById('approachIdea').value.trim();
    const vertical = document.getElementById('approachVertical').value.trim() || 'TBD';
    const geo = document.getElementById('approachGeo').value.trim() || 'TBD';

    if (!idea) return;

    const approaches = [
      { id: 'gov_contract', category: 'Government Contract', title: `Win Government Contracts in ${vertical}`, description: `Use the QLA 'find a need and fill it' principle to identify government agencies spending money on ${vertical}. Government contracts are recurring revenue — Peña calls this 'the annuity business.'`, timeframe: '6-18 months', capital: '$5K-$50K', risk: 'Medium', scale: '$500K-$50M+ annual revenue' },
      { id: 'rollup', category: 'Acquisition Roll-Up', title: `Roll Up Fragmented ${vertical} Businesses`, description: `Use Peña's consolidation principle: find a fragmented industry with many small players, acquire them systematically, create operating leverage, and dominate a region/nation.`, timeframe: '3-6 months to first close', capital: '$250K-$2M', risk: 'Medium-High', scale: '$5M-$100M revenue; exit at 8-12x EBITDA' },
      { id: 'startup', category: 'Startup', title: `Build a ${vertical} Startup`, description: `Use Peña's 'scratch the itch' principle: if you have a better way to solve ${vertical} problems, build it from scratch. This is the highest risk/highest reward approach.`, timeframe: '6-12 months to PMF', capital: '$10K-$250K', risk: 'High', scale: '$0-$1B+ (lottery ticket upside)' },
      { id: 'middleman', category: 'Middleman / Broker', title: `Become the ${vertical} Middleman`, description: `Use Peña's OPM principle: connect buyers and sellers in ${vertical} without owning the underlying asset. You take a fee/percentage for making the introduction.`, timeframe: '1-3 months', capital: '$1K-$10K', risk: 'Low-Medium', scale: '$100K-$10M annual income' },
      { id: 'jv', category: 'Joint Venture', title: `Form ${vertical} Joint Ventures`, description: `Use Peña's 'leverage other people's expertise' principle: find people who already have ${vertical} businesses and partner with them for growth.`, timeframe: '2-6 months', capital: '$25K-$100K', risk: 'Medium', scale: '$500K-$20M across portfolio of JVs' },
      { id: 'license', category: 'Licensing / Franchise', title: `License or Franchise Your ${vertical} Model`, description: `Use Peña's 'duplicate success' principle: once you have a working ${vertical} model, license or franchise it to operators in other markets.`, timeframe: '6-12 months', capital: '$50K-$200K', risk: 'Medium', scale: '$1M-$100M (royalty stream)' },
      { id: 'turnaround', category: 'Turnaround / Distressed', title: `Acquire Distressed ${vertical} Businesses`, description: `Use Peña's 'blood in the streets' principle: find ${vertical} businesses in distress, acquire them cheap, fix operations, and profit from the recovery.`, timeframe: '1-3 months', capital: '$100K-$500K', risk: 'High', scale: '$2M-$50M (buy at 2x, sell at 6-8x)' },
      { id: 'realestate', category: 'Real Estate + Business', title: `Combine Real Estate with ${vertical} Operations`, description: `Use Peña's 'own the dirt' principle: in ${vertical}, real estate is often the most valuable asset. Buy the business AND the real estate.`, timeframe: '3-9 months', capital: '$500K-$5M', risk: 'Medium', scale: '$5M-$50M (combined value)' }
    ];

    const container = document.getElementById('approachCards');
    container.innerHTML = approaches.map(a => `
      <div class="approach-card" onclick="DEALS.selectApproach('${a.id}')">
        <div class="font-bold text-sm font-medium mb-1">${a.category}</div>
        <div class="text-xs font-medium text-gray-200 mb-2">${a.title}</div>
        <div class="grid grid-cols-2 gap-1 text-xs font-medium text-gray-300">
          <div>⏱ ${a.timeframe}</div>
          <div>💰 ${a.capital}</div>
          <div>⚠️ ${a.risk}</div>
          <div>📈 ${a.scale}</div>
        </div>
      </div>
    `).join('');

    document.getElementById('approachOutput').classList.remove('hidden');
  },

  selectApproach(id) {
    document.querySelectorAll('.approach-card').forEach(el => el.classList.remove('selected'));
    event.currentTarget.classList.add('selected');
    this.selectedApproach = id;
  },

  startQLA() {
    const prompt = document.getElementById('qlaPrompt').value.trim();
    if (!prompt) return;

    const dealCard = `🚀 **QLA PROCESS INITIATED**

**Prompt:** ${prompt}

---

**11-Step QLA Cycle:**
1. ✅ Intake — Parsed idea
2. 🔄 Identify — Sourcing targets
3. 🔄 Generalities — Market research
4. 🔄 Specifics — Target details
5. 🔄 Decision — QLA scorecard
6. 🔄 Investigation — Red flags
7. 🔄 Action Plan — Channel + timeline
8. 🔄 Critical Path — Dependencies
9. 🔄 Documents — ES, LOI, NDA
10. 🔄 Outreach — Template generation
11. 🔄 Pipeline — Track progress

**Knowledge Brain:** 2,979 Peña action items active
**AI Brain:** Running QLA methodology
**Next:** Create Discord thread and begin execution`;

    document.getElementById('qlaDealCard').textContent = dealCard;
    document.getElementById('qlaOutput').classList.remove('hidden');
  },

  showOutreach(channel) {
    const templates = {
      email: `Subject: [Company Name] — Acquisition Opportunity

Dear [Owner Name],

I'm reaching out because [Company Name] stands out in the [vertical] space. We're building a consolidation platform and believe your business could be a cornerstone of our strategy.

Would you be open to a brief conversation about your plans for the business?

Best,
[Your Name]`,
      letter: `[Date]

[Owner Name]
[Company Name]
[Address]

Dear [Owner Name],

I've been following [Company Name]'s growth in the [vertical] market. Your reputation precedes you.

We're assembling a group of [vertical] businesses and would welcome the opportunity to discuss how we might work together.

Would you consider a brief, confidential conversation? I'll follow up by phone.

Respectfully,
[Your Name]`,
      phone: `Hi [Owner Name], my name is [Your Name]. I'm calling because we're building a group in the [vertical] space and [Company Name] caught our attention.

I'd love to ask you 3 quick questions:
1. Have you ever thought about selling or partnering?
2. What's most important to you — price, legacy, or speed?
3. Would you be open to a 10-minute call next week?

If now's not a good time, I understand. When would work better?`,
      inperson: `IN-PERSON STRATEGY:

1. Arrive at the office unannounced
2. Ask for the owner by name
3. Have a handwritten letter ready
4. Reference something specific about their business
5. Ask: "Have you ever thought about the future of this business?"
6. Leave your card and a handwritten note
7. Follow up in 7 days

Remember: The ultimate power move is showing up. — Dan Peña`
    };

    document.getElementById('outreachText').textContent = templates[channel] || '';
    document.getElementById('outreachPreview').classList.remove('hidden');
  },

  renderPipeline() {
    this.loadData();
    const list = document.getElementById('pipelineList');
    const companies = this.companies.length;
    let deals = 0, active = 0;

    this.companies.forEach(c => {
      (c.deals || []).forEach(d => {
        deals++;
        if (!['completed', 'killed', 'on_hold'].includes(d.stage)) active++;
      });
    });

    document.getElementById('pipeCompanies').textContent = companies + ' Companies';
    document.getElementById('pipeDeals').textContent = deals + ' Deals';
    document.getElementById('pipeActive').textContent = active + ' Active';

    if (!this.companies.length) {
      list.innerHTML = '<div class="text-gray-300 text-sm font-medium">No deals yet. Launch a deal to get started.</div>';
      return;
    }

    list.innerHTML = this.companies.map(c => `
      <div class="bg-white/15 rounded-lg p-3">
        <div class="flex items-center justify-between mb-2">
          <div class="font-bold text-sm font-medium">${c.company}</div>
          <span class="text-xs font-medium text-gray-300">${c.vertical || 'TBD'}</span>
        </div>
        <div class="flex gap-2 flex-wrap">
          ${(c.deals || []).map(d => `
            <span class="stage-pill stage-${d.stage}">${d.stage}</span>
          `).join('') || '<span class="text-xs font-medium text-gray-300">No deals yet</span>'}
        </div>
      </div>
    `).join('');
  }
};

// Init on load
document.addEventListener('DOMContentLoaded', () => DEALS.init());
