# Medical Equipment Program Case Study Dashboard

## Dashboard Metadata

- Owner: Ryker Iverson
- Audience: Snap Finance Talent Acquisition and management review team
- Business question: Should Snap continue, expand, modify, or tighten the medical equipment provider special underwriting program?
- Data classification: Case-study extract; static and not live production reporting
- Row grain: One row per prequalification application
- Date grain: Prequalification submit date and submit month
- Refresh cadence: Static ad hoc extract packaged with the dashboard
- Source of truth: `data/case_study_dataset.csv`
- Metrics: Definitions are documented in `dashboard_contract.yaml`
- Filters: Prequal Submit Date, Region, Merchant ID, Prequalification Risk Grade, and Swap-In Approval
- Access-control expectations: No secrets required; intended for case-study review only

## Management Summary

The program shows meaningful demand and a workable funnel, but the main leak is the transition from prequalification approval to full application. Swap-in logic produces higher end-to-end completion, but it also concentrates higher-risk applicants and relies heavily on the $1,500 minimum approval floor.

Recommendation: continue the program selectively, focus expansion on stronger merchants and lower-risk segments, monitor F-grade and swap-in exposure, and request repayment/profitability data before broad expansion.

## Required Caveat

The source file does not include repayment or profitability outcomes. The dashboard therefore cannot validate missed payment, delinquency, charge-off, early payoff, actual funded amount, projected amount paid, or profit metrics.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Files

- `app.py`: Streamlit entrypoint, controls, narrative, charts, tables, and downloads.
- `data.py`: Data loading, validation, type cleanup, derived metrics, and aggregations.
- `dashboard_contract.yaml`: Governance metadata, metric definitions, filters, outputs, validation checks, and risk areas.
- `manifest.json`: Runtime metadata for Streamlit-style deployment review.
- `DEPLOYMENT.md`: Local presentation and hosted handoff instructions.
- `.env.example`: Confirms no secrets are required.
- `requirements.txt`: Direct runtime dependencies.
- `requirements-lock.txt`: Reviewed direct deployment pins.
- `data/case_study_dataset.csv`: Local case-study extract used by the dashboard.
- `queries/case_study_reference.sql`: Reference SQL outline for the dashboard metrics.
- `analysis_answers.md`: Written answers to the case-study prompt.

## Maintenance

Keep the dashboard contract aligned with any metric, filter, source, or recommendation change. If repayment data becomes available, add it through `data.py`, document the new source and grain in `dashboard_contract.yaml`, and update the Data Gaps tab.
