# Test Plan

## Manual smoke tests
1. Start with `uvicorn app.main:app --reload`; `/api/health` should return status `ok`.
2. Open the dashboard and confirm empty evidence/timeline states.
3. Upload a supported image/audio/video file with case ID `CASE-001`.
4. Confirm the response contains evidence ID, file size, and a 64-character SHA-256 digest.
5. Refresh the page and confirm the evidence remains in the register.
6. Ask “show the evidence hashes” and confirm only the selected case's records are returned.
7. Export the PDF and confirm it contains the case ID and evidence register.
8. Upload an unsupported file extension and confirm a 400 response.
9. Test a file larger than configured limit and confirm a 413 response.
10. If optional AI dependencies are installed, process known test media and manually compare outputs to ground truth.

## Scientific validation
- Build a labeled evaluation dataset with lawful use and documented provenance.
- Report precision, recall, false-positive/false-negative rates, and confidence calibration by class.
- Evaluate changes across lighting, occlusion, camera quality, accents, noise, languages, and compression.
- Record model name/version, configuration, processing timestamp, and environment.
- Have independent reviewers assess errors and reproducibility.
