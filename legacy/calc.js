// ── Tax band data ────────────────────────────────────────────────────────────

/** Tax bands and NI thresholds keyed by year code (e.g. '2526' for 2025–26). */
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

/** Annual allowance and tapering thresholds per tax year. */
const PENSION_YEARS = {
  '2223': { label: '2022–23', aa: 40000, threshold: 200000, adjustedTrigger: 240000, minAA: 4000 },
  '2324': { label: '2023–24', aa: 60000, threshold: 200000, adjustedTrigger: 260000, minAA: 10000 },
  '2425': { label: '2024–25', aa: 60000, threshold: 200000, adjustedTrigger: 260000, minAA: 10000 },
  '2526': { label: '2025–26', aa: 60000, threshold: 200000, adjustedTrigger: 260000, minAA: 10000 },
};

/** Ordered year keys for pension calculations. */
const PENSION_YEAR_KEYS = Object.keys(PENSION_YEARS);

// ── Tax code validation ──────────────────────────────────────────────────────

/**
 * Validates a UK PAYE tax code.
 *
 * Accepted formats:
 * - Numeric prefix + letter suffix: 1257L, 1000M, 1195N, 500T, 100Y
 * - K codes (negative personal allowance): K100
 * - Fixed-rate codes: BR, D0, D1, NT, SK, SD0, SD1, SD2
 *
 * @param {string} code - The tax code to validate.
 * @returns {boolean} True if the code matches a recognised PAYE format.
 */
function validateTaxCode(code) {
  code = (code || '').toUpperCase().trim();
  if (!code) return false;
  return /^\d+[LMNTY]$/.test(code) || /^\d+K$/.test(code) ||
    /^(BR|D0|D1|NT|SK|SD0|SD1|SD2)$/.test(code);
}

// ── Tax code parser ──────────────────────────────────────────────────────────

/**
 * Parses a UK tax code into a personal allowance and tax mode.
 *
 * Handles standard numeric codes (1257L), marriage allowance transfer
 * (M = +£1,260, N = −£1,260), K codes (negative PA), and fixed-rate
 * codes (BR, D0, D1, NT).
 *
 * When the salary exceeds £100,000, the personal allowance tapers by £1
 * for every £2 above £100,000, down to zero.
 *
 * @param {string} code - The tax code (e.g. '1257L', 'BR', 'K100'). Defaults to '1257L'.
 * @param {number} basePa - The standard personal allowance for the tax year.
 * @param {number} salary - Annual gross salary, used for PA tapering above £100k.
 * @returns {{ pa: number, mode: string }} The effective personal allowance and
 *   tax mode ('normal', 'K', 'BR', 'D0', 'D1', or 'NT').
 */
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

// ── Income tax + NI calculation ──────────────────────────────────────────────

/**
 * Calculates income tax and National Insurance for a single salary.
 *
 * Applies the personal allowance (via `parseCode`), adjusts tax bands
 * for the effective PA (including K-code additions), and sums each band's
 * contribution.
 *
 * @param {number} salary - Annual gross salary. Returns null if ≤ 0 or falsy.
 * @param {string} taxCode - UK tax code (e.g. '1257L').
 * @param {string} yearKey - Tax year key (e.g. '2526').
 * @returns {?{ salary: number, totalTax: number, totalNI: number,
 *   takeHome: number, taxBreakdown: Array<{label: string, amount: number}>,
 *   niBreakdown: Array<{label: string, amount: number}> }}
 *   Breakdown object, or null if the salary is invalid.
 */
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

// ── Pension tapering + carry forward ─────────────────────────────────────────

/**
 * Calculates pension annual allowance tapering and carry forward across
 * multiple tax years.
 *
 * For each year the function:
 * 1. Computes threshold income (taxable income minus employee contributions)
 *    and adjusted income (taxable income plus employer contributions).
 * 2. Tapers the annual allowance if both threshold and adjusted income
 *    exceed their respective triggers — reducing by £1 for every £2 above
 *    the adjusted trigger, down to the minimum AA.
 * 3. Applies carry forward from up to 3 prior years (oldest first) to
 *    offset any excess over the tapered allowance.
 *
 * @param {Object<string, { taxableIncome: string|number, employeeContrib: string|number, employerContrib: string|number }>} inputs
 *   Per-year pension inputs keyed by year code (e.g. '2223').
 * @param {string[]} yearKeys - Ordered array of year keys to process.
 * @param {Object<string, { aa: number, threshold: number, adjustedTrigger: number, minAA: number }>} yearData
 *   Pension thresholds and limits per year.
 * @returns {Object<string, { totalContrib: number, thresholdIncome: number,
 *   adjustedIncome: number, taperedAA: number, cfAvailable: number,
 *   cfUsed: number, cfToNext: number, relievedContrib: number, excess: number }>}
 *   Results keyed by year code.
 */
function calcPension(inputs, yearKeys, yearData) {
  const results = {};
  const unusedRemaining = {};

  for (const key of yearKeys) {
    const p = inputs[key];
    const yr = yearData[key];
    const taxableIncome = parseFloat(p.taxableIncome) || 0;
    const employee = parseFloat(p.employeeContrib) || 0;
    const employer = parseFloat(p.employerContrib) || 0;

    const totalContrib = employee + employer;
    const thresholdIncome = taxableIncome - employee;
    const adjustedIncome = taxableIncome + employer;

    let taperedAA = yr.aa;
    if (thresholdIncome > yr.threshold && adjustedIncome > yr.adjustedTrigger) {
      taperedAA = Math.max(yr.minAA, yr.aa - Math.floor((adjustedIncome - yr.adjustedTrigger) / 2));
    }

    const keyIdx = yearKeys.indexOf(key);
    const priorKeys = yearKeys.slice(Math.max(0, keyIdx - 3), keyIdx);
    const cfAvailable = priorKeys.reduce((sum, k) => sum + (unusedRemaining[k] || 0), 0);

    let cfUsed = 0;
    let excess = 0;

    if (totalContrib > taperedAA) {
      const needed = totalContrib - taperedAA;
      cfUsed = Math.min(cfAvailable, needed);
      excess = needed - cfUsed;
      let remaining = cfUsed;
      for (const pk of priorKeys) {
        if (remaining <= 0) break;
        const use = Math.min(unusedRemaining[pk] || 0, remaining);
        unusedRemaining[pk] -= use;
        remaining -= use;
      }
    }

    const unusedThisYear = Math.max(0, taperedAA - totalContrib);
    unusedRemaining[key] = unusedThisYear;

    const nextPriorKeys = yearKeys.slice(Math.max(0, keyIdx - 2), keyIdx + 1);
    const cfToNext = nextPriorKeys.reduce((sum, k) => sum + (unusedRemaining[k] || 0), 0);

    const relievedContrib = totalContrib - excess;

    results[key] = {
      totalContrib, thresholdIncome, adjustedIncome, taperedAA,
      cfAvailable, cfUsed, cfToNext,
      relievedContrib, excess,
    };
  }

  return results;
}

// ── Exports for Node.js tests (no-op in browser) ────────────────────────────

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { YEARS, PENSION_YEARS, PENSION_YEAR_KEYS, validateTaxCode, parseCode, calcOne, calcPension };
}
