# Deployment Notes

## Recommended External Handoff

For the recruiter, the easiest path is a hosted Streamlit Community Cloud link backed by a private or public GitHub repository containing this folder. Attach `case_study_streamlit_dashboard_email.zip` as a backup only.

## Local Presentation Runbook

```bash
cd "/Users/riverson/Projects/case study/case_study_streamlit_dashboard"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Streamlit Community Cloud

1. Create a GitHub repository.
2. Add the contents of this folder at the repo root or keep the folder and set the app path to `case_study_streamlit_dashboard/app.py`.
3. Confirm `requirements.txt` is committed.
4. Deploy through Streamlit Community Cloud.
5. Send the hosted app URL in the email.

## Posit Connect Consideration

This app includes a static local CSV extract and is built for an external case-study handoff, not a governed production deployment. Before deploying to internal Posit Connect, replace the packaged CSV with an approved prepared asset or warehouse pull, regenerate a full transitive lockfile, and run the Snap Streamlit validation workflow.

## Data And Security

No secrets are required. Do not add credentials or live warehouse access to this package for the recruiter handoff. The provided dataset does not include direct customer PII, but application-level rows should still be treated as case-study data and shared only as intended for the case-study review.
