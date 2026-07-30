/*
Medical equipment program case study queries

Unique identifier:
- Join application records to repayment records on "Application Number".

How to use this file:
- Run Query 0 first to create a simple joined view.
- Then run any of the numbered queries below.
- These queries are intentionally simple and presentation-friendly.

Tables:
- case_study_dataset: one row per prequalification application.
- repayment_results: one row per funded account repayment outcome, with a few duplicate rows removed in the dashboard.
*/

-- Query 0: Build one simple joined view for the analysis.
CREATE OR REPLACE TEMP VIEW joined_application_repayment AS
WITH repayment_dedup AS (
    SELECT DISTINCT *
    FROM repayment_results
)
SELECT
    a."Application Number" AS application_number,
    a.prequal_submit_dt,
    a.prequal_submit_month,
    a.merchant_id,
    a.region,
    a.prequalification_risk_grade,
    a.final_risk_grade,
    a.requested_financing_amount,
    a.prequalification_risk_based_amount,
    a.prequalification_actual_approval_amount,
    a.final_approval_amount,
    a.prequalification_risk_score,
    a.final_risk_score,
    a.credit_score,
    a.is_prequal_approved,
    a.swap_in_approval,
    a.application_status,
    a.submitted_full_application,
    a.is_approved,
    a.is_completed,
    r.pricing_factor,
    r.account_status,
    r.net_funded_amt,
    r.invoice_amount,
    r.invoice_processing_fee,
    r.missed_payment_day_45,
    r.no_payments_first_day_60,
    r.past_due_days_day_90,
    r.past_due_days_day_120,
    r.past_due_30_plus_days_day_120,
    r.early_payoff_day_120,
    r.past_due_ratio_day_180,
    r.projected_amount_paid,
    r.projected_amount_paid - r.net_funded_amt AS profit_proxy,
    1.0 * r.projected_amount_paid / NULLIF(r.net_funded_amt, 0) AS projected_payback_multiple,
    CASE WHEN r.account_status = 'CHARGE_OFF' THEN 1 ELSE 0 END AS charge_off_flag,
    CASE
        WHEN a.prequalification_risk_based_amount < 1500
            AND a.prequalification_actual_approval_amount = 1500
        THEN 1
        ELSE 0
    END AS hit_1500_floor,
    CASE
        WHEN a.is_completed = 'TRUE' THEN a.final_approval_amount
        ELSE 0
    END AS estimated_funded_amount
FROM case_study_dataset a
LEFT JOIN repayment_dedup r
    ON a."Application Number" = r."Application Number";

-- Query 1: Data coverage. Shows how much repayment data is available.
SELECT
    COUNT(*) AS application_rows,
    COUNT(DISTINCT application_number) AS applications,
    SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) AS completed_applications,
    COUNT(DISTINCT CASE WHEN net_funded_amt IS NOT NULL THEN application_number END) AS applications_with_repayment,
    1.0 * COUNT(DISTINCT CASE WHEN net_funded_amt IS NOT NULL THEN application_number END)
        / NULLIF(SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END), 0) AS repayment_coverage_rate
FROM joined_application_repayment;

-- Query 2: Overall program funnel. Answers volume, approvals, completion, and ticket size.
SELECT
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
    AVG(final_approval_amount) AS avg_final_approval_amount,
    SUM(estimated_funded_amount) AS estimated_funded_amount
FROM joined_application_repayment;

-- Query 3: Monthly trend. Shows whether demand and conversion are stable over time.
SELECT
    prequal_submit_month,
    COUNT(*) AS applications,
    SUM(CASE WHEN is_prequal_approved = 'TRUE' THEN 1 ELSE 0 END) AS prequal_approvals,
    SUM(CASE WHEN submitted_full_application = 'TRUE' THEN 1 ELSE 0 END) AS full_applications,
    SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) AS completed_applications,
    1.0 * SUM(CASE WHEN submitted_full_application = 'TRUE' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN is_prequal_approved = 'TRUE' THEN 1 ELSE 0 END), 0) AS continuation_rate,
    1.0 * SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) / COUNT(*) AS completion_rate,
    SUM(estimated_funded_amount) AS estimated_funded_amount
FROM joined_application_repayment
GROUP BY prequal_submit_month
ORDER BY prequal_submit_month;

-- Query 4: Special underwriting / swap-in read. Shows growth value and risk guardrails.
SELECT
    CASE WHEN swap_in_approval = 'TRUE' THEN 'Swap-in' ELSE 'Non-swap' END AS segment,
    COUNT(*) AS applications,
    SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) AS completed_applications,
    1.0 * SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) / COUNT(*) AS completion_rate,
    AVG(prequalification_risk_score) AS avg_prequal_risk_score,
    AVG(final_risk_score) AS avg_final_risk_score,
    AVG(prequalification_actual_approval_amount - prequalification_risk_based_amount) AS avg_underwriting_lift,
    1.0 * SUM(hit_1500_floor) / COUNT(*) AS floor_share,
    SUM(estimated_funded_amount) AS estimated_funded_amount
FROM joined_application_repayment
GROUP BY swap_in_approval
ORDER BY swap_in_approval;

-- Query 5: Repayment by swap-in status. Shows whether special underwriting is paying back.
SELECT
    CASE WHEN swap_in_approval = 'TRUE' THEN 'Swap-in' ELSE 'Non-swap' END AS segment,
    COUNT(DISTINCT application_number) AS repayment_accounts,
    SUM(net_funded_amt) AS total_net_funded,
    SUM(projected_amount_paid) AS total_projected_paid,
    SUM(profit_proxy) AS profit_proxy,
    1.0 * SUM(projected_amount_paid) / NULLIF(SUM(net_funded_amt), 0) AS projected_payback_multiple,
    AVG(CASE WHEN missed_payment_day_45 = 'TRUE' THEN 1 ELSE 0 END) AS missed_payment_day_45_rate,
    AVG(CASE WHEN no_payments_first_day_60 = 'TRUE' THEN 1 ELSE 0 END) AS no_payments_first_day_60_rate,
    AVG(CASE WHEN past_due_30_plus_days_day_120 = 'TRUE' THEN 1 ELSE 0 END) AS past_due_30_plus_day_120_rate,
    AVG(charge_off_flag) AS charge_off_rate
FROM joined_application_repayment
WHERE net_funded_amt IS NOT NULL
GROUP BY swap_in_approval
ORDER BY swap_in_approval;

-- Query 6: Risk profile by prequalification grade. Shows volume, approval behavior, and floor reliance.
SELECT
    prequalification_risk_grade,
    COUNT(*) AS applications,
    SUM(CASE WHEN is_prequal_approved = 'TRUE' THEN 1 ELSE 0 END) AS prequal_approvals,
    SUM(CASE WHEN submitted_full_application = 'TRUE' THEN 1 ELSE 0 END) AS full_applications,
    SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) AS completed_applications,
    1.0 * SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) / COUNT(*) AS completion_rate,
    AVG(prequalification_risk_score) AS avg_prequal_risk_score,
    AVG(final_risk_score) AS avg_final_risk_score,
    1.0 * SUM(hit_1500_floor) / COUNT(*) AS floor_share,
    SUM(estimated_funded_amount) AS estimated_funded_amount
FROM joined_application_repayment
GROUP BY prequalification_risk_grade
ORDER BY prequalification_risk_grade;

-- Query 7: Repayment by risk grade. Shows which grades are healthy and which need guardrails.
SELECT
    prequalification_risk_grade,
    COUNT(DISTINCT application_number) AS repayment_accounts,
    SUM(net_funded_amt) AS total_net_funded,
    SUM(projected_amount_paid) AS total_projected_paid,
    SUM(profit_proxy) AS profit_proxy,
    1.0 * SUM(projected_amount_paid) / NULLIF(SUM(net_funded_amt), 0) AS projected_payback_multiple,
    AVG(CASE WHEN missed_payment_day_45 = 'TRUE' THEN 1 ELSE 0 END) AS missed_payment_day_45_rate,
    AVG(CASE WHEN past_due_30_plus_days_day_120 = 'TRUE' THEN 1 ELSE 0 END) AS past_due_30_plus_day_120_rate,
    AVG(charge_off_flag) AS charge_off_rate
FROM joined_application_repayment
WHERE net_funded_amt IS NOT NULL
GROUP BY prequalification_risk_grade
ORDER BY prequalification_risk_grade;

-- Query 8: Risk migration. Shows whether applicants look better after full application.
SELECT
    CASE
        WHEN submitted_full_application <> 'TRUE' THEN 'No full application'
        WHEN final_risk_grade < prequalification_risk_grade THEN 'Improved'
        WHEN final_risk_grade = prequalification_risk_grade THEN 'Same'
        WHEN final_risk_grade > prequalification_risk_grade THEN 'Worsened'
        ELSE 'No final grade'
    END AS risk_grade_migration,
    COUNT(*) AS applications,
    1.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS application_share
FROM joined_application_repayment
GROUP BY 1
ORDER BY applications DESC;

-- Query 9: Region repayment trend. Shows where expansion looks safer or riskier.
SELECT
    region,
    COUNT(DISTINCT application_number) AS repayment_accounts,
    SUM(net_funded_amt) AS total_net_funded,
    SUM(projected_amount_paid) AS total_projected_paid,
    SUM(profit_proxy) AS profit_proxy,
    1.0 * SUM(projected_amount_paid) / NULLIF(SUM(net_funded_amt), 0) AS projected_payback_multiple,
    AVG(CASE WHEN missed_payment_day_45 = 'TRUE' THEN 1 ELSE 0 END) AS missed_payment_day_45_rate,
    AVG(charge_off_flag) AS charge_off_rate
FROM joined_application_repayment
WHERE net_funded_amt IS NOT NULL
GROUP BY region
ORDER BY profit_proxy DESC;

-- Query 10: Merchant prioritization. Finds high-volume merchants worth expanding or diagnosing.
SELECT
    merchant_id,
    region,
    COUNT(*) AS applications,
    SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) AS completed_applications,
    1.0 * SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) / COUNT(*) AS completion_rate,
    SUM(estimated_funded_amount) AS estimated_funded_amount,
    AVG(prequalification_risk_score) AS avg_prequal_risk_score,
    1.0 * SUM(hit_1500_floor) / COUNT(*) AS floor_share,
    SUM(profit_proxy) AS profit_proxy,
    AVG(charge_off_flag) AS charge_off_rate
FROM joined_application_repayment
GROUP BY merchant_id, region
HAVING COUNT(*) >= 10
ORDER BY estimated_funded_amount DESC;

-- Query 11: Account status mix. Gives management a simple repayment outcome snapshot.
SELECT
    account_status,
    COUNT(DISTINCT application_number) AS accounts,
    1.0 * COUNT(DISTINCT application_number)
        / SUM(COUNT(DISTINCT application_number)) OVER () AS account_share
FROM joined_application_repayment
WHERE net_funded_amt IS NOT NULL
GROUP BY account_status
ORDER BY accounts DESC;

-- Query 12: Management segment read. Combines funnel, risk, and repayment into action buckets.
SELECT
    region,
    merchant_id,
    prequalification_risk_grade,
    CASE WHEN swap_in_approval = 'TRUE' THEN 'Swap-in' ELSE 'Non-swap' END AS segment,
    COUNT(*) AS applications,
    SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) AS completed_applications,
    1.0 * SUM(CASE WHEN is_completed = 'TRUE' THEN 1 ELSE 0 END) / COUNT(*) AS completion_rate,
    SUM(estimated_funded_amount) AS estimated_funded_amount,
    SUM(profit_proxy) AS profit_proxy,
    AVG(prequalification_risk_score) AS avg_prequal_risk_score,
    1.0 * SUM(hit_1500_floor) / COUNT(*) AS floor_share,
    AVG(charge_off_flag) AS charge_off_rate,
    CASE
        WHEN COUNT(*) < 10 THEN 'Needs more volume'
        WHEN SUM(estimated_funded_amount) > 0
            AND AVG(prequalification_risk_score) < 0.25
            AND AVG(COALESCE(charge_off_flag, 0)) < 0.10
        THEN 'Expand selectively'
        WHEN AVG(prequalification_risk_score) >= 0.25
            OR AVG(COALESCE(charge_off_flag, 0)) >= 0.10
            OR 1.0 * SUM(hit_1500_floor) / COUNT(*) >= 0.50
        THEN 'Monitor or tighten'
        ELSE 'Diagnose before expanding'
    END AS management_read
FROM joined_application_repayment
GROUP BY region, merchant_id, prequalification_risk_grade, swap_in_approval
ORDER BY estimated_funded_amount DESC;
