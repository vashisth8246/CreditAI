# Phase 7.2 Test Report

**Date:** 17 October 2026

## Results

- Frontend unit tests: **5 passed** (`npm test`).
- Frontend lint: completed with one existing React `set-state-in-effect` warning in `src/App.tsx`; no lint errors.
- TypeScript build check: passed (`tsc -b`).
- Production Vite build: passed; emitted a 21.86 kB CSS bundle and 286.73 kB JavaScript bundle.
- Backend full pytest suite: still running at the time this report was first written; see the final report for the completed result.
- Live API/browser: model listing and schema loaded; valid synthetic `/v1/predict` request returned a real uncalibrated prediction. The browser rendered the result and provenance.
- Visual verification: desktop overview, desktop prediction screen, model evidence page, and 390 × 844 mobile layouts were viewed in the browser.

## Commands and environment notes

The project path includes `&`, which breaks npm's Windows command-shim resolution for local binaries in this environment. Frontend tests ran through `npm test`; lint, TypeScript, and production build were run through their installed package entry points directly from `frontend/`. The build itself succeeded. The API emitted a Pydantic warning that `schema_extra` is now named `json_schema_extra`; this legacy schema warning did not block API responses.
