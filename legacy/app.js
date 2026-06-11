// ── State ────────────────────────────────────────────────────────────────────

const MAX_COLS = 5;
const S = {
  cols: [{ salary: '', taxCode: '1257L', bonus: '', bonusFreq: '' }],
  taxOpen: false,
  niOpen: false,
  results: null,
  activeTab: 'calculator',
  pension: Object.fromEntries(PENSION_YEAR_KEYS.map(k => [k, { taxableIncome: '', employeeContrib: '', employerContrib: '' }])),
  pensionResults: null,
};

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
    setNote('One or more tax codes are invalid. Please correct them before calculating.', 'var(--red)');
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
    setNote('Results updated.', 'var(--accent)');
    document.getElementById('grid').classList.add('results-appear');
    setTimeout(() => document.getElementById('grid').classList.remove('results-appear'), 300);
  } else {
    setNote('Please enter at least one annual salary.', 'var(--ink-4)');
  }

  render();
}

function updateCol(i, field, val) {
  S.cols[i][field] = val;
  if (S.results) {
    S.results = null;
    setNote('Details changed — press Calculate to update.', 'var(--ink-4)');
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

// ── Pension rendering ───────────────────────────────────────────────────────

function updatePensionField(yearKey, field, value) {
  S.pension[yearKey][field] = value;
  if (S.pensionResults) {
    S.pensionResults = null;
    setPensionNote('Details changed — press Calculate to update.', 'var(--ink-4)');
    renderPension();
  }
}

function setPensionNote(msg, color) {
  const note = document.getElementById('pensionCalcNote');
  note.textContent = msg;
  note.style.color = color;
}

function calculatePension() {
  // Sync inputs from DOM
  document.querySelectorAll('[data-pension-input]').forEach(el => {
    const key = el.dataset.pensionYear;
    const field = el.dataset.pensionField;
    if (S.pension[key]) S.pension[key][field] = el.value;
  });

  S.pensionResults = calcPension(S.pension, PENSION_YEAR_KEYS, PENSION_YEARS);

  const anyInput = PENSION_YEAR_KEYS.some(k => {
    const p = S.pension[k];
    return parseFloat(p.taxableIncome) > 0 || parseFloat(p.employeeContrib) > 0 || parseFloat(p.employerContrib) > 0;
  });

  if (anyInput) {
    setPensionNote('Results updated.', 'var(--accent)');
    document.getElementById('pensionGrid').classList.add('results-appear');
    setTimeout(() => document.getElementById('pensionGrid').classList.remove('results-appear'), 300);
  } else {
    setPensionNote('Please enter income or contributions for at least one year.', 'var(--ink-4)');
  }

  renderPension();
}

const PENSION_ROWS = [
  { key: 'taxableIncome',   label: 'Taxable Income',                input: true, field: 'taxableIncome', placeholder: 'e.g. 300000' },
  { key: 'employeeContrib', label: 'Employee Contributions',        input: true, field: 'employeeContrib', placeholder: 'e.g. 10000' },
  { key: 'employerContrib', label: 'Employer Contributions',        input: true, field: 'employerContrib', placeholder: 'e.g. 30000' },
  { key: 'totalContrib',    label: 'Total Contributions' },
  { key: 'thresholdIncome', label: 'Threshold Income' },
  { key: 'adjustedIncome',  label: 'Adjusted Income' },
  { key: 'taperedAA',       label: 'Available Annual Allowance' },
  { key: 'cfAvailable',     label: 'Carry Forward from Previous' },
  { key: 'cfUsed',          label: 'Carry Forward Used' },
  { key: 'cfToNext',        label: 'Carry Forward to Next Year' },
  { key: 'relievedContrib', label: 'Relieved Contributions' },
  { key: 'excess',          label: 'Excess Over Allowance' },
];

function renderPension() {
  const nYears = PENSION_YEAR_KEYS.length;
  const res = S.pensionResults;
  const grid = document.getElementById('pensionGrid');
  grid.style.gridTemplateColumns = `var(--label-w) repeat(${nYears}, var(--col-w))`;

  const dash = '<span class="result-dash">—</span>';
  const lastColClass = (i) => i === nYears - 1 ? 'no-border-right' : '';

  let h = '';

  // Header row: empty label + one column per year
  h += `<div class="cell cell-colhead label-col"></div>`;
  for (let i = 0; i < nYears; i++) {
    const key = PENSION_YEAR_KEYS[i];
    h += `<div class="cell cell-colhead value-col ${lastColClass(i)}">
      <span class="col-num">${PENSION_YEARS[key].label}</span>
    </div>`;
  }

  // One row per field
  for (let r = 0; r < PENSION_ROWS.length; r++) {
    const row = PENSION_ROWS[r];
    const isLastRow = r === PENSION_ROWS.length - 1;
    const bottomClass = isLastRow ? 'no-border-bottom' : '';

    // Label cell
    h += `<div class="cell ${row.input ? 'cell-input' : ''} label-col ${bottomClass}">${row.label}</div>`;

    // Value cells (one per year)
    for (let i = 0; i < nYears; i++) {
      const key = PENSION_YEAR_KEYS[i];

      if (row.input) {
        h += `<div class="cell cell-input value-col ${bottomClass} ${lastColClass(i)}">
          <div class="field">
            <span class="field-pfx">£</span>
            <input type="number" min="0" step="1000" placeholder="${row.placeholder}"
              value="${esc(S.pension[key][row.field])}"
              data-pension-input data-pension-year="${key}" data-pension-field="${row.field}"
              oninput="updatePensionField('${key}','${row.field}',this.value)">
          </div>
        </div>`;
      } else {
        const val = res ? res[key][row.key] : null;
        h += `<div class="cell value-col ${bottomClass} ${lastColClass(i)}">${res ? fmt(val) : dash}</div>`;
      }
    }
  }

  grid.innerHTML = h;
}

// ── Init ─────────────────────────────────────────────────────────────────────

render();
