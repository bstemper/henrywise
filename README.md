# HenryWise

UK take-home pay and pension calculators. A Streamlit app.

## Run it

```bash
python -m venv venv3 && source venv3/bin/activate
pip install -e ".[dev]"
streamlit run src/henrywise/ui/app.py
```

A browser tab opens at http://localhost:8501.

## Tests

```bash
pytest
ruff check src tests
```

## Layout

```
src/henrywise/
├── tax/          pure calculation — never imports streamlit
│   ├── rates.py      the tax year's numbers  ← edit this each April
│   ├── models.py     TaxBands, TaxRate, TakeHomeResults
│   ├── codes.py      PAYE tax-code parsing
│   └── take_home.py  the calculation
└── ui/           streamlit — never contains a tax number
    ├── app.py        entry point, wiring only
    ├── job_grid.py   the jobs side by side: inputs + results
    └── format.py     money formatting
```

The take-home tab is a grid, not a pair of panels: every row is one field or
one figure, the label sits once in a left-hand column, and each job gets a
column. Both jobs are asked the same questions, so the two answers land side by
side and are read against each other. A job that can't be calculated — an
unsupported tax code, say — shows `—` in its column and an error, and leaves
the other job's column standing.

Two rules keep this honest, and both are worth defending:

1. **`tax/` never imports `streamlit`.** That's what makes the maths testable.
2. **Every number that means pounds or a tax rate lives in `rates.py`.** It is
   the only file you touch when rates change in April. If you find a `12_570`
   anywhere else, it's a bug.

## Scope

Estimate only, not financial advice. Covers income tax (including the £100k
personal-allowance taper), Class 1 employee National Insurance, salary-sacrifice
pension, and multiple bonuses each landing in their own month. Rest of UK only.

NI is charged on the year's earnings after sacrifice. Real NI is worked out per
pay period, so a lumpy bonus month is charged slightly differently in practice;
over a full year on a steady salary the two agree.

Not yet covered: student loans, Scottish/Welsh rates.
