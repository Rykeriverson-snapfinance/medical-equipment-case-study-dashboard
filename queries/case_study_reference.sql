/*
Title: Medical equipment program case study metrics
Purpose: Reference SQL outline for the Streamlit dashboard.
Source: Local CSV table case_study_dataset.
Date field/window: prequal_submit_dt, 2025-06-01 through 2026-07-20 in the supplied extract.
Filters/exclusions: None by default; Streamlit filters are applied interactively.
Output grain: Monthly, risk grade, swap-in, merchant, and management segment summaries.
Limitations: The supplied file has no repayment or profitability fields.
*/

SELECT
    prequal_submit_month,
    COUNT(*) AS applications,
    SUM(CASE WHEN is_prequal_approved = 'TRUE' THEN 1 ELSE 0 END) AS prequal_approvals,
    SUM(CASE WHEN submitted_full_application = 'TRUE' THEN 1 ELSE 0 END) AS full_applications,
    SUM(CASE WHEN is_approved = 'TRUE' THEN 1 ELSE 0 END) AS final_approvals,
    SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) AS completed_applications,
    1.0 * SUM(CASE WHEN is_prequal_approved = 'TRUE' THEN 1 ELSE 0 END) / COUNT(*) AS prequal_approval_rate,
    1.0 * SUM(CASE WHEN submitted_full_application = 'TRUE' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN is_prequal_approved = 'TRUE' THEN 1 ELSE 0 END), 0) AS continuation_rate,
    1.0 * SUM(CASE WHEN is_approved = 'TRUE' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN submitted_full_application = 'TRUE' THEN 1 ELSE 0 END), 0) AS final_approval_rate,
    1.0 * SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) / COUNT(*) AS end_to_end_completion_rate,
    AVG(requested_financing_amount) AS avg_requested_amount,
    AVG(prequalification_actual_approval_amount) AS avg_prequal_approval,
    AVG(final_approval_amount) AS avg_final_approval
FROM case_study_dataset
GROUP BY prequal_submit_month
ORDER BY prequal_submit_month;
