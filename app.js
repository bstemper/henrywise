// ── Tax data ─────────────────────────────────────────────────────────────────

const YEARS = {
  '2526': {
    pa: 12570,
    tax: [
      { label: 'Basic rate · 20%',      rate: 0.20, lo: 12570,  hi: 50270 },
      { label: 'Higher rate · 40%',     rate: 0.40, lo: 50270,  hi: 125140 },
      { label: 'Additional rate · 45%', rate: 0.45, lo: 125140, hi: Infinity },
    ],
    ni: [
      { label: 'Primary rate · 8%',       rate: 0.08, lo: 12570, hi: 50270 },
      { label: 'Above upper limit · 2%',  rate: 0.02, lo: 50270, hi: Infinity },
    ],
  },
  '2627': {
    pa: 12570,
    tax: [
      { label: 'Basic rate · 20%',      rate: 0.20, lo: 12570,  hi: 50270 },
      { label: 'Higher rate · 40%',     rate: 0.40, lo: 50270,  hi: 125140 },
      { label: 'Additional rate · 45%', rate: 0.45, lo: 125140, hi: Infinity },
    ],
    ni: [
      { label: 'Primary rate · 8%',       rate: 0.08, lo: 12570, hi: 50270 },
      { label: 'Above upper limit · 2%',  rate: 0.02, lo: 50270, hi: Infinity },
    ],
  },
};

// ── Pension tapering data ────────────────────────────────────────────────────

const PENSION_YEARS = {
  '2223': { label: '2022–23', aa: 40000, threshold: 200000, adjustedTrigger: 240000, minAA: 4000 },
  '2324': { label: '2023–24', aa: 60000, threshold: 200000, adjustedTrigger: 260000, minAA: 10000 },
  '2425': { label: '2024–25', aa: 60000, threshold: 200000, adjustedTrigger: 260000, minAA: 10000 },
  '2526': { label: '2025–26', aa: 60000, threshold: 200000, adjustedTrigger: 260000, minAA: 10000 },
};
const PENSION_YEAR_KEYS = Object.keys(PENSION_YEARS);

// ── State ────────────────────────────────────────────────────────────────────

const MAX_COLS = 5;
const S = {
  cols: [{ salary: '', taxCode: '1257L', bonus: '', bonusFreq: '' }],
  taxOpen: false,
  niOpen: false,
  results: null,
  activeTab: 'calculator',
  pension: Object.fromEntries(PENSION_YEAR_KEYS.map(k => [k, { grossIncome: '', employerContrib: '', personalContrib: '', pensionUsed: '' }])),
};

// ── Tax code validation ──────────────────────────────────────────────────────

function validateTaxCode(code) {
  code = (code || '').toUpperCase().trim();
  if (!code) return false;
  return /^\d+[LMNTY]$/.test(code) || /^\d+K$/.test(code) ||
    /^(BR|D0|D1|NT|SK|SD0|SD1|SD2)$/.test(code);
}

// ── Tax code parser ──────────────────────────────────────────────────────────

function parseCode(code, basePa, salary) {
  code = (code || '1257L').toUpperCase().trim();
  const suffix = code.replace(/\d/g, '');
  const n = parseInt(code.replace(/\D/g, ''), 10);
  if (suffix === 'NT') return { pa: Infinity, mode: 'NT' };
  if (suffix === 'BR') return { pa: 0,        mode: 'BR' };
  if (suffix === 'D0') return { pa: 0,        mode: 'D0' };
  if (suffix === 'D1') return { pa: 0,        mode: 'D1' };
  if (suffix === 'K')  return { pa: -(n * 10), mode: 'K' };
  let pa = isNaN(n) ? basePa : n * 10;
  if (suffix === 'M') pa += 1260;
  if (suffix === 'N') pa -= 1260;
  if (salary > 100000 && pa > 0)
    pa = Math.max(0, pa - Math.floor((salary - 100000) / 2));
  return { pa, mode: 'normal' };
}

// ── Calculation ──────────────────────────────────────────────────────────────

function calcOne(salary, taxCode, yearKey) {
  if (!salary || salary <= 0) return null;
  const yr = YEARS[yearKey];
  const { pa, mode } = parseCode(taxCode, yr.pa, salary);

  let taxBands;
  if (mode === 'BR') {
    taxBands = [{ label: 'Basic rate · 20%',       rate: 0.20, lo: 0, hi: Infinity }];
  } else if (mode === 'D0') {
    taxBands = [{ label: 'Higher rate · 40%',      rate: 0.40, lo: 0, hi: Infinity }];
  } else if (mode === 'D1') {
    taxBands = [{ label: 'Additional rate · 45%',  rate: 0.45, lo: 0, hi: Infinity }];
  } else if (mode === 'NT') {
    taxBands = [{ label: 'No tax',                 rate: 0,    lo: 0, hi: Infinity }];
  } else {
    const shift = (mode === 'K') ? 0 : pa - yr.pa;
    const extra = (mode === 'K') ? Math.abs(pa) : 0;
    taxBands = yr.tax.map(b => ({
      ...b,
      lo: Math.max(0, b.lo + shift + extra),
      hi: b.hi === Infinity ? Infinity : Math.max(0, b.hi + shift + extra),
    }));
  }

  const taxBreakdown = taxBands.map(b => {
    const taxable = Math.max(0, Math.min(salary, b.hi) - b.lo);
    return { label: b.label, amount: taxable * b.rate };
  });
  const niBreakdown = yr.ni.map(b => {
    const niable = Math.max(0, Math.min(salary, b.hi) - b.lo);
    return { label: b.label, amount: niable * b.rate };
  });
  const totalTax = taxBreakdown.reduce((s, b) => s + b.amount, 0);
  const totalNI  = niBreakdown.reduce((s, b) => s + b.amount, 0);
  return { salary, totalTax, totalNI, takeHome: salary - totalTax - totalNI, taxBreakdown, niBreakdown };
}

// ── Format helpers ───────────────────────────────────────────────────────────

const fmt = v => v == null ? '—' : '£' + Math.round(v).toLocaleString('en-GB');
const esc = s => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const cols = () => S.cols.length;

// ── Render ───────────────────────────────────────────────────────────────────

function render() {
  const yearKey = document.getElementById('taxYear').value;
  const yr = YEARS[yearKey];
  const n = cols();
  const res = S.results;

  const grid = document.getElementById('grid');
  grid.style.gridTemplateColumns = `var(--label-w) repeat(${n}, var(--col-w))`;

  const chev = (open) =>
    `<svg class="chevron ${open ? 'open' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`;

  const C = (cls, content, extra = '') =>
    `<div class="cell ${cls}" ${extra}>${content}</div>`;

  const lastColClass = (i) => i === n - 1 ? 'no-border-right' : '';
  const dash = '<span class="result-dash">—</span>';

  let h = '';

  // Column header row
  h += C('cell-colhead label-col', '');
  for (let i = 0; i < n; i++) {
    const isLast = i === n - 1;
    h += `<div class="cell cell-colhead value-col ${isLast ? 'no-border-right' : ''}">
      <span class="col-num">${n > 1 ? `Option ${String.fromCharCode(65 + i)}` : ''}</span>
      ${n > 1 ? `<button class="btn-danger" onclick="removeCol(${i})" title="Remove column">✕</button>` : ''}
    </div>`;
  }

  // Annual salary row
  h += C('cell cell-input label-col', 'Annual Salary');
  for (let i = 0; i < n; i++) {
    h += `<div class="cell cell-input value-col ${lastColClass(i)}">
      <div class="field">
        <span class="field-pfx">£</span>
        <input type="number" min="0" step="1000" placeholder="e.g. 45000"
          value="${esc(S.cols[i].salary)}"
          data-col-input="${i}" data-field="salary"
          oninput="updateCol(${i},'salary',this.value)">
      </div>
    </div>`;
  }

  // Tax code row
  h += C('cell cell-input label-col', 'Tax Code');
  for (let i = 0; i < n; i++) {
    const tc = S.cols[i].taxCode;
    const tcValid = validateTaxCode(tc);
    const indicator = tc.trim()
      ? `<span class="tax-code-indicator ${tcValid ? 'tax-code-valid' : 'tax-code-invalid'}">${tcValid ? '✓' : '✕'}</span>`
      : '';
    h += `<div class="cell cell-input value-col ${lastColClass(i)}">
      <div class="field">
        <input type="text" placeholder="e.g. 1257L" style="text-transform:uppercase"
          value="${esc(tc)}"
          data-col-input="${i}" data-field="taxCode"
          oninput="updateCol(${i},'taxCode',this.value)">
        ${indicator}
      </div>
    </div>`;
  }

  // Bonus amount row
  h += C('cell cell-input label-col', 'Bonus');
  for (let i = 0; i < n; i++) {
    h += `<div class="cell cell-input value-col ${lastColClass(i)}">
      <div class="field">
        <span class="field-pfx">£</span>
        <input type="number" min="0" step="500" placeholder="e.g. 5000"
          value="${esc(S.cols[i].bonus)}"
          data-col-input="${i}" data-field="bonus"
          oninput="updateCol(${i},'bonus',this.value)">
      </div>
    </div>`;
  }

  // Bonus frequency row (only if any column has a bonus)
  const anyBonus = S.cols.some(c => parseFloat(c.bonus) > 0);
  if (anyBonus) {
    h += C('cell cell-input label-col', 'Bonus Frequency');
    for (let i = 0; i < n; i++) {
      const freq = S.cols[i].bonusFreq || '';
      h += `<div class="cell cell-input value-col ${lastColClass(i)}">
        <div class="field">
          <select data-col-input="${i}" data-field="bonusFreq"
            onchange="updateCol(${i},'bonusFreq',this.value)">
            <option value=""${freq === '' ? ' selected' : ''}>None</option>
            <option value="1"${freq === '1' ? ' selected' : ''}>Annually</option>
            <option value="2"${freq === '2' ? ' selected' : ''}>Semi-annually</option>
            <option value="4"${freq === '4' ? ' selected' : ''}>Quarterly</option>
          </select>
        </div>
      </div>`;
    }
  }

  // Total Income Tax (with toggle chevron)
  h += `<div class="cell cell-total label-col" onclick="toggleS('taxOpen')" style="cursor:pointer;user-select:none;gap:8px">
    ${chev(S.taxOpen)} Total Income Tax
  </div>`;
  for (let i = 0; i < n; i++) {
    h += C(`cell cell-total value-col ${lastColClass(i)}`, res ? fmt(res[i]?.totalTax) : dash);
  }

  // Tax band detail rows (expandable)
  if (S.taxOpen) {
    yr.tax.forEach((b, bi) => {
      h += C('cell cell-band label-col', b.label);
      for (let i = 0; i < n; i++) {
        const val = res ? res[i]?.taxBreakdown[bi]?.amount ?? null : null;
        h += C(`cell cell-band value-col ${lastColClass(i)}`, res ? fmt(val) : dash);
      }
    });
  }

  // Total NI (with toggle chevron)
  h += `<div class="cell cell-total label-col" onclick="toggleS('niOpen')" style="cursor:pointer;user-select:none;gap:8px">
    ${chev(S.niOpen)} Total NI
  </div>`;
  for (let i = 0; i < n; i++) {
    h += C(`cell cell-total value-col ${lastColClass(i)}`, res ? fmt(res[i]?.totalNI) : dash);
  }

  // NI band detail rows (expandable)
  if (S.niOpen) {
    yr.ni.forEach((b, bi) => {
      h += C('cell cell-band label-col', b.label);
      for (let i = 0; i < n; i++) {
        const val = res ? res[i]?.niBreakdown[bi]?.amount ?? null : null;
        h += C(`cell cell-band value-col ${lastColClass(i)}`, res ? fmt(val) : dash);
      }
    });
  }

  // Take-home annual
  h += C('cell cell-takehome label-col', 'Take-Home Pay');
  for (let i = 0; i < n; i++) {
    h += C(`cell cell-takehome value-col ${lastColClass(i)}`, res ? fmt(res[i]?.takeHome) : dash);
  }

  // Take-home per month (salary only)
  const anyBonusResult = res && res.some(r => r && r.bonusFreq > 0);
  h += C(`cell cell-monthly label-col ${anyBonusResult ? '' : 'no-border-bottom'}`, '↳ per month');
  for (let i = 0; i < n; i++) {
    h += C(`cell cell-monthly value-col ${lastColClass(i)} ${anyBonusResult ? '' : 'no-border-bottom'}`,
      res ? fmt(res[i] ? res[i].salaryTakeHome / 12 : null) : dash);
  }

  // Bonus month row (only if any result has bonus)
  if (anyBonusResult) {
    h += C('cell cell-monthly label-col no-border-bottom', '↳ bonus month');
    for (let i = 0; i < n; i++) {
      const r = res ? res[i] : null;
      const val = r && r.bonusFreq > 0
        ? (r.salaryTakeHome / 12) + (r.bonusNet / r.bonusFreq)
        : (r ? r.salaryTakeHome / 12 : null);
      h += C(`cell cell-monthly value-col ${lastColClass(i)} no-border-bottom`, res ? fmt(val) : dash);
    }
  }

  grid.innerHTML = h;
  renderToolbar();
}

function renderToolbar() {
  let btn = document.getElementById('addColBtn');
  if (!btn) {
    btn = document.createElement('button');
    btn.id = 'addColBtn';
    btn.className = 'btn btn-outline';
    btn.onclick = addCol;
    document.querySelector('.toolbar').appendChild(btn);
  }
  if (S.cols.length >= MAX_COLS) {
    btn.style.display = 'none';
  } else {
    btn.style.display = '';
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> Add column`;
  }
}

// ── Actions ──────────────────────────────────────────────────────────────────

function setNote(msg, color) {
  const note = document.getElementById('calcNote');
  note.textContent = msg;
  note.style.color = color;
}

function calculate() {
  document.querySelectorAll('[data-col-input]').forEach(el => {
    const i = +el.dataset.colInput;
    const field = el.dataset.field;
    if (S.cols[i]) S.cols[i][field] = el.value;
  });

  const hasInvalid = S.cols.some(c => c.taxCode.trim() && !validateTaxCode(c.taxCode));
  if (hasInvalid) {
    setNote('One or more tax codes are invalid. Please correct them before calculating.', '#dc2626');
    return;
  }

  const yearKey = document.getElementById('taxYear').value;
  S.results = S.cols.map(c => {
    const sal = parseFloat(c.salary);
    if (isNaN(sal) || sal <= 0) return null;
    const bonus = parseFloat(c.bonus) || 0;
    const freqNum = parseInt(c.bonusFreq) || 0;
    const totalAnnualBonus = bonus > 0 && freqNum > 0 ? bonus * freqNum : 0;
    const base = calcOne(sal, c.taxCode, yearKey);
    if (totalAnnualBonus <= 0) return { ...base, salaryTakeHome: base.takeHome, bonusNet: 0, bonusFreq: 0 };
    const combined = calcOne(sal + totalAnnualBonus, c.taxCode, yearKey);
    const bonusNet = combined.takeHome - base.takeHome;
    return { ...combined, salaryTakeHome: base.takeHome, bonusNet, bonusFreq: freqNum };
  });

  const anyValid = S.results.some(r => r !== null);
  if (anyValid) {
    setNote('Results updated.', 'var(--green-600)');
    document.getElementById('grid').classList.add('results-appear');
    setTimeout(() => document.getElementById('grid').classList.remove('results-appear'), 300);
  } else {
    setNote('Please enter at least one annual salary.', 'var(--gray-400)');
  }

  render();
}

function updateCol(i, field, val) {
  S.cols[i][field] = val;
  if (S.results) {
    S.results = null;
    setNote('Details changed — press Calculate to update.', 'var(--gray-400)');
  }
  if (field === 'bonus') {
    render();
    return;
  }
  if (field === 'taxCode') {
    const input = document.querySelector(`[data-col-input="${i}"][data-field="taxCode"]`);
    if (input) {
      const wrapper = input.closest('.field');
      let indicator = wrapper.querySelector('.tax-code-indicator');
      const trimmed = val.trim();
      if (trimmed) {
        const valid = validateTaxCode(val);
        if (!indicator) {
          indicator = document.createElement('span');
          indicator.className = 'tax-code-indicator';
          wrapper.appendChild(indicator);
        }
        indicator.className = `tax-code-indicator ${valid ? 'tax-code-valid' : 'tax-code-invalid'}`;
        indicator.textContent = valid ? '✓' : '✕';
      } else if (indicator) {
        indicator.remove();
      }
    }
  }
}

function addCol() {
  if (S.cols.length >= MAX_COLS) return;
  S.cols.push({ salary: '', taxCode: '1257L', bonus: '', bonusFreq: '' });
  S.results = null;
  render();
}

function removeCol(i) {
  if (S.cols.length <= 1) return;
  S.cols.splice(i, 1);
  S.results = null;
  render();
}

function toggleS(key) {
  S[key] = !S[key];
  render();
}

// ── Tab switching ────────────────────────────────────────────────────────────

function switchTab(tab) {
  S.activeTab = tab;
  document.getElementById('tab-calculator').style.display = tab === 'calculator' ? '' : 'none';
  document.getElementById('tab-pension').style.display = tab === 'pension' ? '' : 'none';
  document.querySelectorAll('.tab').forEach(el => {
    el.classList.toggle('active', el.dataset.tab === tab);
  });
  if (tab === 'pension') renderPension();
}

// ── Pension calculation ─────────────────────────────────────────────────────

function calcPension() {
  const results = {};
  for (const key of PENSION_YEAR_KEYS) {
    const p = S.pension[key];
    const yr = PENSION_YEARS[key];
    const gross = parseFloat(p.grossIncome) || 0;
    const employer = parseFloat(p.employerContrib) || 0;
    const personal = parseFloat(p.personalContrib) || 0;
    const used = parseFloat(p.pensionUsed) || 0;

    const thresholdIncome = gross - personal;
    const adjustedIncome = gross + employer;

    let taperedAA = yr.aa;
    if (thresholdIncome > yr.threshold && adjustedIncome > yr.adjustedTrigger) {
      taperedAA = Math.max(yr.minAA, yr.aa - Math.floor((adjustedIncome - yr.adjustedTrigger) / 2));
    }

    const unused = Math.max(0, taperedAA - used);
    results[key] = { thresholdIncome, adjustedIncome, taperedAA, unused };
  }

  // Carry forward for current year (last key)
  const currentKey = PENSION_YEAR_KEYS[PENSION_YEAR_KEYS.length - 1];
  const priorKeys = PENSION_YEAR_KEYS.slice(0, -1);
  const carryForward = priorKeys.reduce((sum, k) => sum + results[k].unused, 0);
  const totalAvailable = results[currentKey].taperedAA + carryForward;
  results._carryForward = carryForward;
  results._totalAvailable = totalAvailable;

  return results;
}

// ── Pension rendering ───────────────────────────────────────────────────────

function updatePensionField(yearKey, field, value) {
  S.pension[yearKey][field] = value;
  renderPension();
}

function renderPension() {
  const n = PENSION_YEAR_KEYS.length;
  const res = calcPension();
  const grid = document.getElementById('pensionGrid');
  grid.style.gridTemplateColumns = `var(--label-w) repeat(${n}, var(--col-w))`;

  const C = (cls, content) => `<div class="cell ${cls}">${content}</div>`;
  const lastColClass = (i) => i === n - 1 ? 'no-border-right' : '';
  const currentIdx = n - 1;

  let h = '';

  // Column headers
  h += C('cell-colhead label-col', '');
  for (let i = 0; i < n; i++) {
    const key = PENSION_YEAR_KEYS[i];
    h += `<div class="cell cell-colhead value-col ${lastColClass(i)}">
      <span class="col-num">${PENSION_YEARS[key].label}</span>
    </div>`;
  }

  // Input rows
  const inputRows = [
    { label: 'Gross Income', field: 'grossIncome', placeholder: 'e.g. 300000' },
    { label: 'Employer Contributions', field: 'employerContrib', placeholder: 'e.g. 30000' },
    { label: 'Personal Contributions', field: 'personalContrib', placeholder: 'e.g. 10000' },
  ];

  for (const row of inputRows) {
    h += C('cell cell-input label-col', row.label);
    for (let i = 0; i < n; i++) {
      const key = PENSION_YEAR_KEYS[i];
      h += `<div class="cell cell-input value-col ${lastColClass(i)}">
        <div class="field">
          <span class="field-pfx">£</span>
          <input type="number" min="0" step="1000" placeholder="${row.placeholder}"
            value="${esc(S.pension[key][row.field])}"
            oninput="updatePensionField('${key}','${row.field}',this.value)">
        </div>
      </div>`;
    }
  }

  // Computed rows
  h += C('cell label-col', 'Threshold Income');
  for (let i = 0; i < n; i++) {
    const key = PENSION_YEAR_KEYS[i];
    h += C(`cell value-col ${lastColClass(i)}`, fmt(res[key].thresholdIncome));
  }

  h += C('cell label-col', 'Adjusted Income');
  for (let i = 0; i < n; i++) {
    const key = PENSION_YEAR_KEYS[i];
    h += C(`cell value-col ${lastColClass(i)}`, fmt(res[key].adjustedIncome));
  }

  h += C('cell label-col', 'Annual Allowance');
  for (let i = 0; i < n; i++) {
    const key = PENSION_YEAR_KEYS[i];
    h += C(`cell value-col ${lastColClass(i)}`, fmt(res[key].taperedAA));
  }

  // Pension used input
  h += C('cell cell-input label-col', 'Pension Used');
  for (let i = 0; i < n; i++) {
    const key = PENSION_YEAR_KEYS[i];
    h += `<div class="cell cell-input value-col ${lastColClass(i)}">
      <div class="field">
        <span class="field-pfx">£</span>
        <input type="number" min="0" step="1000" placeholder="e.g. 20000"
          value="${esc(S.pension[key].pensionUsed)}"
          oninput="updatePensionField('${key}','pensionUsed',this.value)">
      </div>
    </div>`;
  }

  // Unused allowance
  h += C('cell label-col', 'Unused Allowance');
  for (let i = 0; i < n; i++) {
    const key = PENSION_YEAR_KEYS[i];
    h += C(`cell value-col ${lastColClass(i)}`, fmt(res[key].unused));
  }

  // Carry forward (only current year)
  h += C('cell cell-total label-col', 'Carry Forward Available');
  for (let i = 0; i < n; i++) {
    h += C(`cell cell-total value-col ${lastColClass(i)}`, i === currentIdx ? fmt(res._carryForward) : '—');
  }

  // Total available (only current year)
  h += C('cell cell-takehome label-col no-border-bottom', 'Total Available');
  for (let i = 0; i < n; i++) {
    h += C(`cell cell-takehome value-col ${lastColClass(i)} no-border-bottom`, i === currentIdx ? fmt(res._totalAvailable) : '—');
  }

  grid.innerHTML = h;
}

// ── Init ─────────────────────────────────────────────────────────────────────

render();
