# Phase 6.1 Initial State Record

**Recorded:** 13 October 2026, before Phase 6.1 edits.

- Workspace root: `CreditAI`.
- Version control: the workspace is **not** a Git working tree (`git rev-parse --is-inside-work-tree` failed); no Git diff can establish change isolation.
- Frontend: React 19 + TypeScript + Vite; five tab screens (Overview, Data Readiness, Risk Scoring, Evaluation, Architecture); no charting or frontend test dependencies in `frontend/package.json`.
- Phase 5 modules present under `src/data_intake`, `src/data_quality`, `src/temporal_audit`, `src/evaluation`, and `src/qualification`; `tests/test_phase5_data_validation.py` is present.
- Saved verified LendingClub benchmark files: `reports/phase_2_3_metrics.csv`, `reports/phase_2_3_split_summary.csv`, `reports/phase_2_3_1_metric_verification.csv`, plus Phase 2.2/2.3 audit files. No saved loan-level prediction-score file or ROC/PR curve-coordinate artifact was found in `reports/`.
- Phase 5 reports exist, including the 98-test historical report and Phase 5.2 frontend verification. Those reports are prior evidence, not a current Phase 6.1 test run.
- The project has LendingClub CSV/XLSX, Taiwan UCI, German UCI, credit approval, aggregate RBI/NPCI, CreditMitra sample, and synthetic data under `Data/`; no Phase 6.1 candidate files were present locally at inspection.
- `/v1/score` is an existing FastAPI contract and must remain `not_validated` with a null probability.

## SHA-256 baselines for protected existing files

These hashes were captured before editing. The three frontend application files and frontend README below are expected to change in Phase 6.1. The frontend environment file, scoring API implementation/contract, and prior benchmark/Phase 5 reports are protected and were verified byte-identical after implementation.

| File | SHA-256 |
|---|---|
| `frontend/src/App.tsx` | `2CE84761E7DC3EC6D870B289B3EDE0B299A6B1EF3403796D527BF6ECF8EEABDC` |
| `frontend/src/App.css` | `7988EF4340A0E7F8BB81A89FE9FF6325BF2F78D9C7BEF284B17FCBE587DD565C` |
| `frontend/src/index.css` | `27C043B1ACC612B80F9FAED76228A6D52EB590DA33A084E8FD6A3D36AED0FFB3` |
| `frontend/README.md` | `FA8AAC78B8BE1993010B57F41000A243ECBA006F6731513FE4EC91E788BF2517` |
| `frontend/.env.example` | `F144792596089DA6A0D48F44FB77387A18C752A4657C7247D470E876802E9D16` |
| `src/api/app.py` | `FAD234A401C84E5901743889A1BFA2E745C5DC5E6127864E8334AA7DC17629F3` |
| `src/api/contract.py` | `34E422C99573B30C0DE63004F7A463B2BBEA07E21007F113236957D7EA444A88` |
| `reports/phase_2_3_metrics.csv` | `3857BA22DB60CCC9C0BE0C8DCCA22864CCFE42A3DF954D88DACA84F3E2F9477B` |
| `reports/phase_2_3_benchmark_report.md` | `A093748FD2FA89EBA916B0C4A1FAD8A29F1DD3C5C7BDEED5AAA9EF3E69221D6A` |
| `reports/phase_5_test_report.md` | `D5CB4EB33D91AF34902D2707A60F6A8B64ABBD16A38285E05DA3B0A33F65C585` |
| `reports/phase_5_2_frontend_verification.md` | `D471CFDC3F8F8B99075159BA3971B679DCADCBCC28F8F69B342C29B16A24F501` |
| `reports/phase_2_3_1_independent_audit.md` | `AD5714BD46B501E2A625018BC089404FC68BD52B00465D62DB8E6DC0599EA82A` |
