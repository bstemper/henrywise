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

// ── State ────────────────────────────────────────────────────────────────────

const MAX_COLS = 5;
const S = {
  cols: [{ salary: '', taxCode: '1257L' }],
  taxOpen: false,
  niOpen: false,
  results: null,
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

  // Take-home monthly (last row)
  h += C('cell cell-monthly label-col no-border-bottom', '↳ per month');
  for (let i = 0; i < n; i++) {
    h += C(`cell cell-monthly value-col ${lastColClass(i)} no-border-bottom`, res ? fmt(res[i] ? res[i].takeHome / 12 : null) : dash);
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
    return isNaN(sal) || sal <= 0 ? null : calcOne(sal, c.taxCode, yearKey);
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
  S.cols.push({ salary: '', taxCode: '1257L' });
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

// ── Init ─────────────────────────────────────────────────────────────────────

render();
