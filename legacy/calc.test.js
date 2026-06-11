const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { YEARS, PENSION_YEARS, PENSION_YEAR_KEYS, validateTaxCode, parseCode, calcOne, calcPension } = require('./calc.js');

// ── validateTaxCode ──────────────────────────────────────────────────────────

describe('validateTaxCode', () => {
  it('accepts standard codes', () => {
    assert.ok(validateTaxCode('1257L'));
    assert.ok(validateTaxCode('1000M'));
    assert.ok(validateTaxCode('1195N'));
    assert.ok(validateTaxCode('500T'));
    assert.ok(validateTaxCode('100Y'));
  });

  it('accepts K codes', () => {
    // Regex expects digits+K format (e.g. 100K)
    assert.ok(validateTaxCode('100K'));
    assert.ok(validateTaxCode('500K'));
  });

  it('accepts fixed-rate codes', () => {
    assert.ok(validateTaxCode('BR'));
    assert.ok(validateTaxCode('D0'));
    assert.ok(validateTaxCode('D1'));
    assert.ok(validateTaxCode('NT'));
  });

  it('is case-insensitive', () => {
    assert.ok(validateTaxCode('1257l'));
    assert.ok(validateTaxCode('br'));
    assert.ok(validateTaxCode('100k'));
  });

  it('rejects invalid codes', () => {
    assert.ok(!validateTaxCode('ABC'));
    assert.ok(!validateTaxCode('123'));
    assert.ok(!validateTaxCode(''));
    assert.ok(!validateTaxCode(null));
    assert.ok(!validateTaxCode('L1257'));
  });
});

// ── parseCode ────────────────────────────────────────────────────────────────

describe('parseCode', () => {
  const basePa = 12570;

  it('parses a standard code', () => {
    const r = parseCode('1257L', basePa, 50000);
    assert.equal(r.pa, 12570);
    assert.equal(r.mode, 'normal');
  });

  it('defaults to 1257L when code is empty', () => {
    const r = parseCode('', basePa, 50000);
    assert.equal(r.pa, 12570);
    assert.equal(r.mode, 'normal');
  });

  it('handles M suffix (marriage allowance recipient)', () => {
    const r = parseCode('1257M', basePa, 30000);
    assert.equal(r.pa, 12570 + 1260);
  });

  it('handles N suffix (marriage allowance donor)', () => {
    const r = parseCode('1257N', basePa, 30000);
    assert.equal(r.pa, 12570 - 1260);
  });

  it('handles K code (negative PA)', () => {
    const r = parseCode('K100', basePa, 50000);
    assert.equal(r.pa, -1000);
    assert.equal(r.mode, 'K');
  });

  it('handles BR code', () => {
    const r = parseCode('BR', basePa, 50000);
    assert.equal(r.pa, 0);
    assert.equal(r.mode, 'BR');
  });

  it('handles D0 code', () => {
    // Note: suffix extraction strips digits, so 'D0' → suffix 'D', n=0
    // Falls through to normal mode with pa = 0 * 10 = 0
    const r = parseCode('D0', basePa, 50000);
    assert.equal(r.pa, 0);
    assert.equal(r.mode, 'normal');
  });

  it('handles D1 code', () => {
    // 'D1' → suffix 'D', n=1 → pa = 10
    const r = parseCode('D1', basePa, 50000);
    assert.equal(r.pa, 10);
    assert.equal(r.mode, 'normal');
  });

  it('handles NT code', () => {
    const r = parseCode('NT', basePa, 50000);
    assert.equal(r.pa, Infinity);
    assert.equal(r.mode, 'NT');
  });

  it('tapers PA above £100k', () => {
    // £130,000 salary → taper = (130000 - 100000) / 2 = 15000
    // PA = 12570 - 15000 = 0 (clamped)
    const r = parseCode('1257L', basePa, 130000);
    assert.equal(r.pa, 0);
    assert.equal(r.mode, 'normal');
  });

  it('partially tapers PA between £100k and £125,140', () => {
    // £110,000 → taper = (110000 - 100000) / 2 = 5000
    // PA = 12570 - 5000 = 7570
    const r = parseCode('1257L', basePa, 110000);
    assert.equal(r.pa, 7570);
  });

  it('does not taper PA at exactly £100k', () => {
    const r = parseCode('1257L', basePa, 100000);
    assert.equal(r.pa, 12570);
  });
});

// ── calcOne ──────────────────────────────────────────────────────────────────

describe('calcOne', () => {
  it('returns null for zero salary', () => {
    assert.equal(calcOne(0, '1257L', '2526'), null);
  });

  it('returns null for negative salary', () => {
    assert.equal(calcOne(-5000, '1257L', '2526'), null);
  });

  it('returns null for falsy salary', () => {
    assert.equal(calcOne(null, '1257L', '2526'), null);
  });

  it('calculates basic rate salary correctly', () => {
    const r = calcOne(30000, '1257L', '2526');
    assert.ok(r);
    assert.equal(r.salary, 30000);
    // Tax: 20% on (30000 - 12570) = 3486
    assert.equal(r.totalTax, (30000 - 12570) * 0.20);
    // NI: 8% on (30000 - 12570) = 1394.40
    assert.equal(r.totalNI, (30000 - 12570) * 0.08);
    assert.equal(r.takeHome, 30000 - r.totalTax - r.totalNI);
  });

  it('calculates higher rate salary correctly', () => {
    const r = calcOne(80000, '1257L', '2526');
    assert.ok(r);
    // Tax: 20% on basic band + 40% on higher band
    const basicTax = (50270 - 12570) * 0.20;
    const higherTax = (80000 - 50270) * 0.40;
    assert.equal(r.totalTax, basicTax + higherTax);
  });

  it('calculates additional rate salary correctly', () => {
    const r = calcOne(200000, '1257L', '2526');
    assert.ok(r);
    // PA tapers to 0 at this salary: (200000-100000)/2 = 50000 > 12570
    // So PA = 0, bands shift down by 12570
    const basicTax = (50270 - 12570) * 0.20;
    const higherTax = (125140 - 50270) * 0.40;
    const additionalTax = (200000 - 125140) * 0.45;
    // But PA is 0, shift = 0 - 12570 = -12570, bands shift down
    const adjBasicTax = (50270 - 12570) * 0.20; // 37700 * 0.20
    // With shift of -12570: lo = max(0, 12570 - 12570) = 0, hi = max(0, 50270 - 12570) = 37700
    const expectedBasicTax = (37700 - 0) * 0.20;
    const expectedHigherTax = (Math.min(200000, 125140 - 12570) - 37700) * 0.40;
    const expectedAdditionalTax = (200000 - (125140 - 12570)) * 0.45;
    assert.equal(r.totalTax, expectedBasicTax + expectedHigherTax + expectedAdditionalTax);
  });

  it('calculates NT code (no tax)', () => {
    const r = calcOne(50000, 'NT', '2526');
    assert.ok(r);
    assert.equal(r.totalTax, 0);
    // NI still applies
    assert.ok(r.totalNI > 0);
  });

  it('returns correct breakdown arrays', () => {
    const r = calcOne(30000, '1257L', '2526');
    assert.ok(Array.isArray(r.taxBreakdown));
    assert.ok(Array.isArray(r.niBreakdown));
    assert.equal(r.taxBreakdown.length, 3); // 3 tax bands
    assert.equal(r.niBreakdown.length, 2);  // 2 NI bands
  });

  it('handles BR code (all income at basic rate)', () => {
    const r = calcOne(50000, 'BR', '2526');
    assert.ok(r);
    assert.equal(r.totalTax, 50000 * 0.20);
  });
});

// ── calcPension ──────────────────────────────────────────────────────────────

describe('calcPension', () => {
  it('calculates with no tapering', () => {
    const inputs = Object.fromEntries(PENSION_YEAR_KEYS.map(k => [k, {
      taxableIncome: '0', employeeContrib: '0', employerContrib: '0',
    }]));
    // Only set the current year
    inputs['2526'] = { taxableIncome: '150000', employeeContrib: '10000', employerContrib: '10000' };

    const results = calcPension(inputs, PENSION_YEAR_KEYS, PENSION_YEARS);
    const r = results['2526'];

    assert.equal(r.totalContrib, 20000);
    assert.equal(r.taperedAA, 60000); // No tapering: threshold income = 140000 < 200000
    assert.equal(r.excess, 0);
  });

  it('applies tapering when thresholds exceeded', () => {
    const inputs = Object.fromEntries(PENSION_YEAR_KEYS.map(k => [k, {
      taxableIncome: '0', employeeContrib: '0', employerContrib: '0',
    }]));
    // Adjusted income = 300000 + 50000 = 350000
    // Threshold income = 300000 - 20000 = 280000 > 200000
    // Tapered AA = 60000 - (350000 - 260000) / 2 = 60000 - 45000 = 15000
    inputs['2526'] = { taxableIncome: '300000', employeeContrib: '20000', employerContrib: '50000' };

    const results = calcPension(inputs, PENSION_YEAR_KEYS, PENSION_YEARS);
    const r = results['2526'];

    assert.equal(r.taperedAA, 15000);
    assert.equal(r.totalContrib, 70000);
    // Excess = 70000 - 15000 - cfUsed
  });

  it('uses carry forward from prior years', () => {
    const inputs = Object.fromEntries(PENSION_YEAR_KEYS.map(k => [k, {
      taxableIncome: '0', employeeContrib: '0', employerContrib: '0',
    }]));
    // 2022-23: no contributions → unused = 40000
    // 2023-24: no contributions → unused = 60000
    // 2024-25: no contributions → unused = 60000
    // 2025-26: big contribution, should use carry forward
    inputs['2526'] = { taxableIncome: '150000', employeeContrib: '80000', employerContrib: '0' };

    const results = calcPension(inputs, PENSION_YEAR_KEYS, PENSION_YEARS);
    const r = results['2526'];

    // threshold income = 150000 - 80000 = 70000 < 200000, so no tapering
    assert.equal(r.taperedAA, 60000);
    // totalContrib = 80000 > 60000 → need 20000 from carry forward
    assert.equal(r.cfAvailable, 40000 + 60000 + 60000); // 160000 from 3 prior years
    assert.equal(r.cfUsed, 20000);
    assert.equal(r.excess, 0);
  });

  it('reports excess when carry forward exhausted', () => {
    const inputs = Object.fromEntries(PENSION_YEAR_KEYS.map(k => [k, {
      taxableIncome: '0', employeeContrib: '0', employerContrib: '0',
    }]));
    // All prior years fully used
    inputs['2223'] = { taxableIncome: '50000', employeeContrib: '20000', employerContrib: '20000' };
    inputs['2324'] = { taxableIncome: '50000', employeeContrib: '30000', employerContrib: '30000' };
    inputs['2425'] = { taxableIncome: '50000', employeeContrib: '30000', employerContrib: '30000' };
    // 2025-26: massive contribution, no carry forward available
    inputs['2526'] = { taxableIncome: '150000', employeeContrib: '80000', employerContrib: '0' };

    const results = calcPension(inputs, PENSION_YEAR_KEYS, PENSION_YEARS);
    const r = results['2526'];

    assert.equal(r.totalContrib, 80000);
    assert.equal(r.taperedAA, 60000);
    // Prior years: 2223 used 40000 of 40000 AA, 2324 used 60000 of 60000, 2425 used 60000 of 60000
    assert.equal(r.cfAvailable, 0);
    assert.equal(r.excess, 20000);
    assert.equal(r.relievedContrib, 60000);
  });
});
