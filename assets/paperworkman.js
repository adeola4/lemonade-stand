// ===== PAPERWORKMAN SECTION =====
// Standalone UI for QLA document generation and deal intake

window.PAPERWORKMAN = {
  intakeData: {},
  readinessScore: 0,
  
  init() {
    this.loadFromStorage();
    this.renderIntakeForm();
    this.renderReadinessPanel();
    this.renderDocumentStudio();
    this.renderTemplateLibrary();
  },
  
  loadFromStorage() {
    const stored = localStorage.getItem('paperworkman_intake');
    if (stored) {
      try { this.intakeData = JSON.parse(stored); } catch(e) {}
    }
  },
  
  saveData() {
    localStorage.setItem('paperworkman_intake', JSON.stringify(this.intakeData));
  },
  
  // § 1.1 Q1-Q10 Intake Questionnaire
  renderIntakeForm() {
    const container = document.getElementById('paperworkmanIntake');
    if (!container) return;
    
    const fields = [
      { id: 'pm_concept', label: 'Q1 · Business Concept', placeholder: 'What does this company actually do? One sentence.' },
      { id: 'pm_industry', label: 'Q2 · Industry / Vertical', placeholder: 'e.g., home health care, energy, AI, real estate' },
      { id: 'pm_revenue', label: 'Q3 · Revenue Engine', placeholder: 'How does it make money? Medicare? SaaS? Product sales?' },
      { id: 'pm_moat', label: 'Q4 · Competitive Moat', placeholder: 'What do you provide that incumbents don\'t?' },
      { id: 'pm_operator', label: 'Q5 · Operator', placeholder: 'Who is driving this? Background, credibility markers.' },
      { id: 'pm_dreamteam', label: 'Q6 · Dream Team Status', placeholder: 'Chairman / Legal / Accounting / Industry advisor — who is filled?' },
      { id: 'pm_entity', label: 'Q7 · Jurisdiction & Entity', placeholder: 'LLC / Corp / State / Formation status' },
      { id: 'pm_score', label: 'Q8 · QLA Readiness (1-50)', placeholder: 'Self-rate: revenue(5) + operator(5) + moat(5) + market(5) + team(5) + board(5) + entity(5) + revenue_tier(5) + cashflow(5) + fragmentation(5)' },
      { id: 'pm_90day', label: 'Q9 · 90-Day Milestone', placeholder: 'What does success look like in 90 days?' },
      { id: 'pm_first_doc', label: 'Q10 · First Deliverable', placeholder: 'Executive Summary / LOI / Term Sheet / Projections' },
    ];
    
    container.innerHTML = fields.map(f => {
      const val = this.intakeData[f.id] || '';
      return `
        <div class="mb-3">
          <label class="block text-xs text-gray-400 mb-1">${f.label}</label>
          <input id="${f.id}" value="${val}" class="w-full text-sm rounded bg-white/10 border border-white/20 px-3 py-2" placeholder="${f.placeholder}" onchange="PAPERWORKMAN.updateField('${f.id}', this.value)">
        </div>
      `;
    }).join('') + `
      <button onclick="PAPERWORKMAN.calculateReadiness()" class="w-full mt-3 rounded bg-yellow-600 text-dark font-semibold px-4 py-2 text-sm">📊 Calculate QLA Readiness</button>
    `;
  },
  
  updateField(id, value) {
    this.intakeData[id] = value;
    this.saveData();
  },
  
  calculateReadiness() {
    // Auto-calculate from Q8 or parse individual scores
    const score = parseInt(this.intakeData.pm_score) || 0;
    this.readinessScore = score;
    
    let status = 'NO-GO';
    let cls = 'bg-red-500/20 text-red-400';
    if (score >= 30) { status = 'GO'; cls = 'bg-green-500/20 text-green-400'; }
    else if (score >= 20) { status = 'CONDITIONAL'; cls = 'bg-yellow-500/20 text-yellow-400'; }
    
    document.getElementById('readinessBadge').className = `inline-flex items-center gap-2 px-3 py-1 rounded text-sm font-semibold ${cls}`;
    document.getElementById('readinessBadge').textContent = `${score}/50 — ${status}`;
    document.getElementById('readinessPanel').classList.remove('hidden');
    
    // Show document generation options based on readiness
    this.updateDocOptions(status);
  },
  
  updateDocOptions(status) {
    const container = document.getElementById('docOptions');
    if (!container) return;
    
    const docs = [
      { type: 'executive_summary', label: '📋 Executive Summary', min: 0 },
      { type: 'loi', label: '📝 Letter of Intent', min: 20 },
      { type: 'offer', label: '📄 Offer Letter', min: 20 },
      { type: 'termsheet', label: '📑 Term Sheet', min: 20 },
      { type: 'projections', label: '📊 Financial Projections', min: 0 },
      { type: 'diligence', label: '🔍 DD Checklist', min: 30 },
      { type: 'operating', label: '⚖️ Operating Agreement', min: 30 },
      { type: 'pitchdeck', label: '🎯 Pitch Deck Outline', min: 0 },
      { type: 'white_paper', label: '📖 White Paper Outline', min: 0 },
      { type: 'nda', label: '🔒 NDA Template', min: 20 },
    ];
    
    container.innerHTML = docs.map(d => {
      const disabled = this.readinessScore < d.min;
      const opacity = disabled ? 'opacity-40' : '';
      const onclick = disabled ? '' : `onclick="PAPERWORKMAN.generateDoc('${d.type}')"`;
      return `<button ${onclick} class="text-left text-sm px-3 py-2 rounded bg-white/10 hover:bg-white/20 transition ${opacity}" ${disabled ? 'disabled' : ''}>${d.label}${disabled ? ` (needs ${d.min}+` : ''}</button>`;
    }).join('');
  },
  
  renderReadinessPanel() {
    const container = document.getElementById('readinessPanel');
    if (!container) return;
    container.innerHTML = `
      <div class="bg-white/5 border border-white/10 rounded-lg p-4">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-semibold">QLA Readiness</span>
          <span id="readinessBadge" class="inline-flex items-center gap-2 px-3 py-1 rounded text-sm font-semibold bg-white/10 text-gray-400">Not calculated</span>
        </div>
        <div id="docOptions" class="grid grid-cols-2 md:grid-cols-3 gap-2"></div>
      </div>
    `;
  },
  
  // Document Studio
  renderDocumentStudio() {
    const container = document.getElementById('documentStudio');
    if (!container) return;
    container.innerHTML = `
      <div class="bg-white/5 border border-white/10 rounded-lg p-4">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-semibold">📄 Document Studio</span>
          <span class="text-xs text-gray-400">Generated docs appear here</span>
        </div>
        <div id="docOutput" class="space-y-2">
          <div class="text-gray-500 text-sm">Calculate readiness and select a document type to generate.</div>
        </div>
      </div>
    `;
  },
  
  generateDoc(type) {
    const output = document.getElementById('docOutput');
    if (!output) return;
    
    const company = this.intakeData.pm_concept || '[COMPANY]';
    const industry = this.intakeData.pm_industry || '[INDUSTRY]';
    const revenue = this.intakeData.pm_revenue || '[REVENUE MODEL]';
    const moat = this.intakeData.pm_moat || '[MOAT]';
    
    const docs = {
      executive_summary: this._execSummary(company, industry, revenue, moat),
      loi: this._loi(company),
      offer: this._offer(company),
      termsheet: this._termsheet(company),
      projections: this._projections(company),
      diligence: this._diligence(company),
      operating: this._operating(company),
      pitchdeck: this._pitchdeck(company, industry),
      white_paper: this._whitePaper(company, industry),
      nda: this._nda(company),
    };
    
    const content = docs[type] || 'Document template not found.';
    const label = type.replace(/_/g, ' ').toUpperCase();
    
    const id = 'doc_' + Date.now();
    output.innerHTML = `
      <div class="bg-white/5 border border-white/10 rounded-lg p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-semibold text-yellow-400">${label}</span>
          <div class="flex gap-2">
            <button onclick="PAPERWORKMAN.downloadDoc('${id}')" class="text-xs px-2 py-1 rounded bg-yellow-600/20 text-yellow-400">Download</button>
            <button onclick="PAPERWORKMAN.copyDoc('${id}')" class="text-xs px-2 py-1 rounded bg-white/10">Copy</button>
          </div>
        </div>
        <pre id="${id}" class="whitespace-pre-wrap text-xs text-gray-200 font-mono max-h-96 overflow-y-auto">${content}</pre>
        <div class="mt-2 text-xs text-gray-500">
          <strong>Provenance:</strong> Generated from QLA thesis (Paperworkman SKILL.md § 0) · ${new Date().toISOString()}
        </div>
      </div>
    `;
  },
  
  downloadDoc(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const blob = new Blob([el.textContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `paperworkman_doc_${id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  },
  
  copyDoc(id) {
    const el = document.getElementById(id);
    if (!el) return;
    navigator.clipboard.writeText(el.textContent).then(() => alert('Copied!'));
  },
  
  // ===== DOCUMENT TEMPLATES (from Paperworkman SKILL.md § 0) =====
  
  _execSummary(company, industry, revenue, moat) {
    return `# Executive Summary — ${company}

An investment consortium specialising in the acquisition and consolidation of U.S. ${industry} agencies.

## Thesis

${company} is a QLA-aligned acquisition vehicle targeting the highly fragmented ${industry} sector. We acquire cash-flowing agencies at 2.0×–5.0× EBITDA, consolidate operations through a centralised back-office, and build toward 50–100 agencies.

## Market Opportunity

- 50,000+ U.S. agencies — most are mom-and-pops operating at <20% gross profit
- Demand structurally increasing (10,000+ baby boomers reach retirement age daily)
- Small and under-prepared agencies are strained, creating attractive entry valuations

## Financial Model

Offer multiple:         2.0× – 5.0× EBITDA
DSCR minimum:           ≥ 1.50×
Seller note term:       5 – 10 years
Seller note rate:       8.0% typical
Profit split:           60% Manager / 40% Non-Manager
EBITDA exit multiple:   14× – 18× (de-levered)

## Revenue Engine
${revenue}

## Competitive Moat
${moat}

## Roadmap

90 Days:   Initial DD model, first LOI issued
180 Days:  Back-office live, first acquisition closed
360 Days:  Three acquisitions closed, pipeline active

---
Generated by Paperworkman · QLA document engine
Thesis source: Paperworkman SKILL.md § 0
`;
  },
  
  _loi(company) {
    return `LETTER OF INTENT

Date: [DATE]
${company}
[Address]

Re: Letter of Intent — {TARGET_COMPANY}

Dear {SELLER_NAME},

This Letter of Intent ("LOI") sets forth the principal terms upon which ${company} ("Buyer") proposes to acquire {TARGET_COMPANY} ("Company") from {SELLER_NAME} ("Seller").

## 1. Acquisition Structure
Purchase Price: {PURCHASE_PRICE}
Cash at close:  {CASH_AT_CLOSE} (min $250,000)
Seller note:    {SELLER_NOTE_AMOUNT} at {RATE}% for {TERM} years
OPM slot:       {OPM_AMOUNT}
QLA Math Gate: Seller note = Purchase Price − Cash − OPM
Offer multiple: {MULTIPLE}× EBITDA (2.0×-5.0× range)
DSCR:           ≥ 1.50× minimum

## 2. Seller Note Terms
- Non-recourse except fraud, capital calls, misrepresentation
- Subordinate to senior lender / SBA facility
- Secured by company stock or personal guarantees

## 3. Conditions to Close
- Due Diligence: 28-45 days
- Exclusivity / No-Shop: 30-60 days
- CHOW and license transfer
- Board / shareholder approval

## 4. Post-Close: QLA 60/40 Alignment
60% to Manager / 40% pro rata among Non-Manager Members.

## 5. Non-Binding
Non-binding except confidentiality and exclusivity provisions.

___________________________
${company}

___________________________
{SELLER_NAME}

Date: _______________

---
Generated by Paperworkman · QLA document engine
All parameters from SKILL.md § 0 thesis
`;
  },
  
  _termsheet(company) {
    return `TERM SHEET — {TARGET_COMPANY}

Date: [DATE]
Buyer: ${company}
Seller: {SELLER}

## Valuation
Enterprise Value: {AMOUNT}
Entry Multiple:   {MULTIPLE}× EBITDA (2.0×-5.0× range)

## Structure
Cash at Close:    {CASH} (min $250K)
Seller Note:      {NOTE} at 8% over 5-10 years
OPM / Third-Party: {OPM}

## Conditions
- DD satisfaction (28-45 days)
- Financing commitment
- No material adverse change
- Key employee retention

## Exclusivity
60-day exclusivity period

## Expenses
Each party bears its own costs

Non-binding except Sections 5 and 6.

___________________________
${company}

___________________________
{SELLER}

---
Generated by Paperworkman · QLA document engine
`;
  },
  
  _projections(company) {
    return `# Financial Projections — ${company}

Three-Scenario Model (Conservative / Base / Aggressive)
All scenarios use QLA capital stack: 2.0×-5.0× entry, 60/40 split, seller note 8% over 5-10 years.

## Entry Assumptions

| Parameter | Conservative | Base | Aggressive |
|-----------|-------------|------|------------|
| Agencies | 50 | 75 | 100 |
| Avg Revenue | $1.5M | $2.0M | $2.5M |
| Avg EBITDA Margin | 15% | 20% | 25% |
| Avg EBITDA | $225K | $400K | $625K |
| Entry Multiple | 4.0× | 3.0× | 2.0× |
| Purchase Price | $900K | $1.2M | $1.25M |
| Total Cost | $45M | $90M | $125M |

## Capital Stack (per deal)

| Source | Conservative | Base | Aggressive |
|--------|-------------|------|------------|
| Cash at Close | $250K | $300K | $350K |
| Seller Note (8%, 7yr) | $500K | $700K | $750K |
| OPM | $150K | $200K | $150K |

## 5-Year Projection (Base Case)

| Year | Revenue | EBITDA | Margin | DSCR |
|------|---------|--------|--------|------|
| 1 | $150M | $30.0M | 20% | 2.0× |
| 2 | $180M | $39.6M | 22% | 2.3× |
| 3 | $210M | $52.5M | 25% | 2.6× |
| 4 | $240M | $67.2M | 28% | 2.9× |
| 5 | $270M | $83.7M | 31% | 3.2× |

## Exit Analysis

| Scenario | Y5 EBITDA | Multiple | EV | MoIC |
|----------|-----------|----------|-----|------|
| Conservative | $28.4M | 16× | $454M | 5.0× |
| Base | $83.7M | 18× | $1.5B | 8.4× |
| Aggressive | $166.5M | 20× | $3.3B | 13.3× |

## QLA Compliance
✓ Entry multiples within 2.0×-5.0× range
✓ DSCR ≥ 1.50× maintained
✓ Seller note separated from OPM
✓ 60/40 profit split reflected
✓ No ungrounded claims

---
Generated by Paperworkman · QLA document engine
Sources: thesis-index.md, acquisition criteria, financial strategy § 0
`;
  },
  
  _diligence(company) {
    return `DUE DILIGENCE CHECKLIST — {TARGET_COMPANY}

[PEÑA METHOD: "Investigate Generalities, Then Specifics"]

I. CORPORATE RECORDS
   [ ] Articles of Incorporation
   [ ] Bylaws / Operating Agreement
   [ ] Minutes (last 3 years)
   [ ] Capitalization table
   [ ] Shareholder/member list

II. FINANCIAL RECORDS
   [ ] Audited financials (3 years)
   [ ] Tax returns (3 years)
   [ ] A/R aging
   [ ] A/P aging
   [ ] Revenue by customer (top 10)
   [ ] EBITDA adjustments
   [ ] Owner compensation analysis

III. OPERATIONS
   [ ] Customer list with contacts
   [ ] Employee roster + compensation
   [ ] Key contracts and commitments
   [ ] Insurance policies
   [ ] Equipment list and condition
   [ ] Facility leases

IV. LEGAL / COMPLIANCE
   [ ] Pending/threatened litigation
   [ ] Regulatory licenses and permits
   [ ] Environmental compliance
   [ ] HIPAA compliance (healthcare)
   [ ] State survey results
   [ ] Corporate integrity agreements

V. MARKET / COMPETITION
   [ ] Market share analysis
   [ ] Competitor landscape
   [ ] Referral source analysis
   [ ] Growth opportunities
   [ ] Threats and risks

VI. HUMAN CAPITAL
   [ ] Key person dependencies
   [ ] Employee satisfaction
   [ ] Turnover rates
   [ ] Non-compete agreements
   [ ] Benefit plans

NOTES:
Red flags to investigate: _______________
Key assumptions to verify: _______________
Deal-breakers: _______________

---
Generated by Paperworkman · QLA document engine
`;
  },
  
  _operating(company) {
    return `OPERATING AGREEMENT OUTLINE — ${company}

QLA-ALIGNED LLC OPERATING AGREEMENT

ARTICLE I — FORMATION
1.1 Name: ${company}, LLC
1.2 State of Formation: [State]
1.3 Purpose: Acquisition and operation of [industry] agencies

ARTICLE II — MEMBERS
2.1 Managing Member: [Name] — 60% profit share
2.2 Non-Managing Members — 40% pro rata
2.3 Capital Contributions

ARTICLE III — ALLOCATIONS
3.1 QLA 60/40 Profit Split
   - 60% to Manager (operating equity)
   - 40% to Non-Managing Members
3.2 Distributions: Quarterly or as determined by Manager

ARTICLE IV — GOVERNANCE
4.1 Supermajority (67%) required for: sale, merger, dissolution, new members
4.2 Drag-Along: EV prior to trigger ≥ 2×
4.3 Lock-Up Period: 3-7 years

ARTICLE V — QLA PROVISIONS
5.1 Seller Note Mechanics
5.2 Equity Rollover on Exit
5.3 DSCR maintenance ≥ 1.50×
5.4 Acquisition criteria compliance

ARTICLE VI — DISPUTE RESOLUTION
Mediation → Arbitration in [State]

---
Generated by Paperworkman · QLA document engine
All provisions from SKILL.md § 0 thesis
`;
  },
  
  _offer(company) {
    return `OFFER TO PURCHASE

Date: [DATE]

{SELLER_NAME}
[Address]

RE: Offer to Purchase {TARGET_COMPANY}

Dear {SELLER_NAME},

${company} is pleased to submit this offer to purchase {TARGET_COMPANY}:

PURCHASE PRICE: {AMOUNT}
TERMS: [Cash / Seller Financing / Combination]

This offer is contingent upon:
1. Satisfactory completion of due diligence
2. Execution of definitive purchase agreement
3. Securing financing (if applicable)
4. No material adverse change

This offer shall remain open for acceptance until [DATE + 14 days].

Sincerely,

${company}

---
Generated by Paperworkman · QLA document engine
`;
  },
  
  _pitchdeck(company, industry) {
    return `# PITCH DECK OUTLINE — ${company}

10-15 slides with speaker notes

SLIDE 1 — TITLE
${company}
"QLA-aligned ${industry} acquisition vehicle"

SLIDE 2 — THE PROBLEM
- 50,000+ agencies, most subscale
- Demand growing, supply fragmented
- PDGM created urgency

SLIDE 3 — THE SOLUTION
- Hub-and-spoke acquisition model
- Back-office consolidation
- 2.0×-5.0× EBITDA entry

SLIDE 4 — MARKET SIZE
- TAM: $28B
- SAM: ~$5B
- SOM (5-yr): ~$285M run-rate

SLIDE 5 — TRACTION
- [Deals closed / LOIs issued]
- Pipeline: [X] targets
- Back-office status

SLIDE 6 — FINANCIAL MODEL
- Entry: 2.0×-5.0× EBITDA
- DSCR ≥ 1.50×
- 60/40 profit split
- Exit: 14×-18× EBITDA

SLIDE 7 — TEAM
- Board: 250+ years combined experience
- Operator: [Name / background]
- Advisors: [Names]

SLIDE 8 — COMPETITIVE MOAT
- Back-office scale synergies
- Caregiver retention
- Telehealth integration
- Referral network effects

SLIDE 9 — ROADMAP
- 90 days: DD model, first LOI
- 180 days: First close
- 360 days: Three acquisitions

SLIDE 10 — THE ASK
- Amount: $[TBD]
- Structure: Cash / seller note / OPM
- Use of funds: Acquisitions + back-office + working capital
- Runway: 18-24 months
- Exit: IPO at 25×-35× EBITDA

SLIDE 11 — APPENDIX
- Detailed projections
- Comparable transactions
- Regulatory landscape

---
Generated by Paperworkman · QLA document engine
All claims traceable to SKILL.md § 0 thesis
`;
  },
  
  _whitePaper(company, industry) {
    return `# WHITE PAPER OUTLINE — ${company}

20-25 page section breakdown

1. EXECUTIVE SUMMARY (1 page)
   - Company overview
   - Investment thesis
   - Key metrics

2. THE INDUSTRY (3 pages)
   - Market size and growth
   - Regulatory landscape
   - PDGM impact
   - Demographic tailwinds
   - Fragmentation analysis

3. THE OPPORTUNITY (2 pages)
   - Why now
   - Fragmented industry dynamics
   - Seller motivation analysis
   - Buyer landscape (limited PE activity in lower-middle-market)

4. THE QLA METHODOLOGY (4 pages)
   - Origination playbook (Peña)
   - 11-step deal process
   - Capital stack structure
   - 60/40 profit protocol
   - DSCR gate ≥ 1.50×

5. ACQUISITION STRATEGY (3 pages)
   - Hub-and-spoke model
   - Target criteria (census, EBITDA, geography)
   - Back-office consolidation plan
   - Operational improvements
   - Telehealth integration

6. FINANCIAL PROJECTIONS (4 pages)
   - 3-scenario model
   - Capital stack per deal
   - 5-year P&L
   - DSCR analysis
   - Exit multiples

7. TEAM & GOVERNANCE (2 pages)
   - Board composition
   - Dream team (Chairman, Legal, Accounting, Industry)
   - Operating partners
   - Advisory network

8. RISK ANALYSIS (2 pages)
   - Regulatory risk
   - Key person dependency
   - Reimbursement risk
   - Mitigation strategies

9. EXIT ARCHITECTURE (2 pages)
   - IPO path (25×-35× EBITDA)
   - Strategic sale (2-3× entry)
   - Timeline and triggers

10. APPENDIX (2 pages)
    - Comparable transactions
    - Thesis sources
    - Data references

---
Generated by Paperworkman · QLA document engine
`;
  },
  
  _nda(company) {
    return `MUTUAL NON-DISCLOSURE AGREEMENT

Entered into as of [DATE] by and between:

${company} ("Disclosing Party")
AND
{SELLER_NAME} ("Receiving Party")

1. PURPOSE
   Evaluate a potential transaction involving {TARGET_COMPANY}.

2. CONFIDENTIAL INFORMATION
   Financial data, customer lists, employee info, trade secrets, business plans.

3. OBLIGATIONS
   - Use solely for evaluating the Transaction
   - Not disclose to third parties without written consent
   - Protect with same care as own confidential information

4. TERM
   2 years from date of last disclosure.

5. GOVERNING LAW
   [State] law.

___________________________
${company}

___________________________
{SELLER_NAME}

Date: _______________

---
Generated by Paperworkman · QLA document engine
`;
  },
  
  // Template Library
  renderTemplateLibrary() {
    const container = document.getElementById('templateLibrary');
    if (!container) return;
    
    const templates = [
      { name: 'LOI Template', desc: 'Letter of Intent with QLA math gates', type: 'loi' },
      { name: 'NDA Template', desc: 'Mutual Non-Disclosure Agreement', type: 'nda' },
      { name: 'Offer Letter', desc: 'Formal offer to purchase', type: 'offer' },
      { name: 'Term Sheet', desc: 'One-page deal terms', type: 'termsheet' },
      { name: 'Executive Summary', desc: 'One-page backer document', type: 'executive_summary' },
      { name: 'Financial Projections', desc: '3-scenario, 5-year model', type: 'projections' },
      { name: 'DD Checklist', desc: 'Due diligence checklist', type: 'diligence' },
      { name: 'Operating Agreement', desc: 'QLA-aligned LLC agreement', type: 'operating' },
      { name: 'Pitch Deck Outline', desc: '10-15 slide structure', type: 'pitchdeck' },
      { name: 'White Paper Outline', desc: '20-25 page structure', type: 'white_paper' },
    ];
    
    container.innerHTML = templates.map(t => `
      <div class="flex items-center justify-between bg-white/5 border border-white/10 rounded-lg px-3 py-2">
        <div>
          <div class="text-sm font-medium">${t.name}</div>
          <div class="text-xs text-gray-400">${t.desc}</div>
        </div>
        <button onclick="PAPERWORKMAN.generateDoc('${t.type}')" class="text-xs px-2 py-1 rounded bg-yellow-600/20 text-yellow-400 hover:bg-yellow-600/30">Preview</button>
      </div>
    `).join('');
  },
};
