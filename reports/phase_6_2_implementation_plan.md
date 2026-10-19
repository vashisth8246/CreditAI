# CreditAI Phase 6.2 — Implementation Plan

**Date:** 16 October 2026
**Status:** Planning Phase
**Objective:** Improve frontend UI/UX, enhance data discovery, add functional interactions, and strengthen research infrastructure

---

## 1. Current State Assessment

### 1.1 Backend Status
- **Tests:** 98 passed, 5 warnings (verified 2026-10-16)
- **API Contract:** Preserved, `/v1/score` returns `not_validated` with `default_probability: null`
- **Phase 5 Modules:** Data intake, quality validation, temporal audit, evaluation metrics, qualification gate - all implemented
- **Phase 6.1:** Dataset inventory, feature inventory, 8-view frontend, aggregate JSON artifacts

### 1.2 Frontend Status
- **Framework:** React 19.2.8 + TypeScript 6.0.2 + Vite 8.3.0
- **Views:** 8 views implemented (Executive Overview, Data Discovery, Portfolio Intelligence, Model Lab, Risk Explorer, Explainability, Monitoring, Architecture/Audit)
- **Charts:** Custom SVG/CSS components (no external chart library)
- **Data Artifacts:** 3 JSON files in `frontend/public/data/` (inventory, features, LendingClub summary)
- **Frontend Tests:** 5 passed (analytics unit tests)
- **Build:** Production build successful (266.64 kB JS, 28.89 kB CSS)

### 1.3 Dataset Inventory
- **Total Datasets:** 22 (DS001-DS017 local, EXT001-EXT003 external)
- **Qualified for Research:** DS001 (LendingClub), DS003 (Taiwan UCI)
- **Blocked:** 13 datasets (synthetic, aggregate-only, damaged, unauthorized)
- **Review Required:** 4 datasets (German credit variants, OpenML, PLOS SHG)
- **No Authorized Indian Data:** Confirmed - no qualified Indian borrower-level repayment dataset

### 1.4 Known Limitations
- No automated frontend UI tests (only analytics unit tests)
- No backend research endpoints (only `/health` and `/v1/score`)
- No live API integration in current environment (loopback restriction)
- No real-time data refresh mechanism
- No experiment comparison interface
- No monitoring data (future-ready only)
- No SHAP/explainability artifacts for display

---

## 2. Proposed Changes

### 2.1 Priority 1: UI/UX Improvements (High Impact, Low Risk)

#### A. Enhanced Navigation
- **Current:** Persistent navigation rail with icons
- **Improvement:** Add keyboard shortcuts, breadcrumb navigation, view descriptions
- **Files:** `frontend/src/App.tsx`, `frontend/src/App.css`
- **Risk:** Low - visual enhancement only

#### B. Better Empty States
- **Current:** Generic empty state component
- **Improvement:** Context-specific empty states with actionable next steps
- **Files:** `frontend/src/App.tsx`, `frontend/src/App.css`
- **Risk:** Low - visual enhancement only

#### C. Improved Loading States
- **Current:** Basic loading indicator
- **Improvement:** Skeleton loaders, progress indicators, cancelable operations
- **Files:** `frontend/src/App.tsx`, `frontend/src/App.css`
- **Risk:** Low - visual enhancement only

#### D. Enhanced Error States
- **Current:** Basic error message
- **Improvement:** Retry buttons, error details, suggested actions
- **Files:** `frontend/src/App.tsx`, `frontend/src/App.css`
- **Risk:** Low - visual enhancement only

### 2.2 Priority 2: Data Discovery Enhancements (High Impact, Medium Risk)

#### A. Advanced Search and Filtering
- **Current:** Basic filterInventory function
- **Improvement:** Multi-column search, filter presets, saved filters
- **Files:** `frontend/src/analytics.ts`, `frontend/src/App.tsx`, `frontend/src/DatasetInventoryTable.ts`
- **Risk:** Medium - requires careful testing of filter logic

#### B. Dataset Detail View
- **Current:** Table row only
- **Improvement:** Modal or dedicated detail view with full metadata
- **Files:** `frontend/src/App.tsx`, `frontend/src/App.css`
- **Risk:** Low - new component, isolated from existing logic

#### C. Qualification Workflow Visualization
- **Current:** Static qualification decision text
- **Improvement:** Visual workflow showing qualification steps and status
- **Files:** `frontend/src/App.tsx`, `frontend/src/App.css`
- **Risk:** Low - visualization only

### 2.3 Priority 3: Model Lab Enhancements (Medium Impact, Medium Risk)

#### A. Experiment Comparison Table
- **Current:** Single experiment display
- **Improvement:** Side-by-side comparison of multiple experiments
- **Files:** `frontend/src/App.tsx`, `frontend/src/analytics.ts`
- **Risk:** Medium - requires careful data structure design

#### B. Metric Visualization
- **Current:** Numeric display only
- **Improvement:** Bar charts for metric comparison, sparklines for trends
- **Files:** `frontend/src/App.tsx`, `frontend/src/App.css`
- **Risk:** Low - new chart components

#### C. Dataset/Target Context
- **Current:** Basic metadata
- **Improvement:** Detailed context for each experiment (dataset, target, split, cohort)
- **Files:** `frontend/src/App.tsx`, `frontend/public/data/phase_6_1_lendingclub_summary.json` (may need enhancement)
- **Risk:** Low - display enhancement only

### 2.4 Priority 4: Backend Research Endpoints (Medium Impact, High Risk)

#### A. Readiness Summary Endpoint
- **Current:** No endpoint
- **Improvement:** `GET /api/readiness` returning system readiness status
- **Files:** `src/api/app.py`, `tests/test_api_integration.py`
- **Risk:** High - requires new endpoint, testing, documentation

#### B. Dataset Inventory Endpoint
- **Current:** Static JSON file
- **Improvement:** `GET /api/datasets` returning current inventory from CSV
- **Files:** `src/api/app.py`, `src/api/readiness.py` (new), `tests/test_api_integration.py`
- **Risk:** High - requires new endpoint, CSV parsing, error handling

#### C. Evaluation Results Endpoint
- **Current:** Static JSON file
- **Improvement:** `GET /api/evaluation` returning saved evaluation artifacts
- **Files:** `src/api/app.py`, `src/api/evaluation.py` (new), `tests/test_api_integration.py`
- **Risk:** High - requires new endpoint, artifact parsing, error handling

**Decision:** Defer backend endpoints to later phase. Frontend can use static JSON files for now. Focus on UI/UX and frontend-only enhancements first.

### 2.5 Priority 5: Monitoring and Explainability (Low Impact, Low Risk)

#### A. Monitoring Interface Design
- **Current:** Future-ready placeholder
- **Improvement:** Detailed design document for future implementation
- **Files:** `reports/phase_6_2_monitoring_design.md` (new)
- **Risk:** None - documentation only

#### B. Explainability Interface Design
- **Current:** Future-ready placeholder
- **Improvement:** Detailed design document for future implementation
- **Files:** `reports/phase_6_2_explainability_design.md` (new)
- **Risk:** None - documentation only

---

## 3. Files Affected

### 3.1 Frontend Source Files
- `frontend/src/App.tsx` - Main application component (current: 276 lines, will expand)
- `frontend/src/App.css` - Application styles (current: 28,357 bytes, will expand)
- `frontend/src/analytics.ts` - Utility functions (current: 2,323 bytes, may expand)
- `frontend/src/DatasetInventoryTable.ts` - Table component (current: 2,320 bytes, may expand)

### 3.2 Frontend Data Files
- `frontend/public/data/phase_6_1_dataset_inventory.json` - May need enhancement for detail view
- `frontend/public/data/phase_6_1_lendingclub_summary.json` - May need enhancement for comparison

### 3.3 Documentation Files
- `reports/phase_6_2_implementation_plan.md` - This file
- `reports/phase_6_2_final_report.md` - To be created
- `reports/phase_6_2_test_report.md` - To be created
- `frontend/README.md` - To be updated with new features

### 3.4 Backend Files (Deferred)
- `src/api/app.py` - No changes in this phase
- `src/api/contract.py` - No changes in this phase
- `tests/test_api_integration.py` - No changes in this phase

---

## 4. Risks and Mitigations

### 4.1 Risk: Breaking Existing Functionality
- **Mitigation:** Run full test suite before and after changes
- **Mitigation:** Use feature flags for major changes
- **Mitigation:** Incremental commits with clear messages

### 4.2 Risk: Performance Degradation
- **Mitigation:** Profile rendering performance
- **Mitigation:** Use React.memo for expensive components
- **Mitigation:** Lazy load non-critical views

### 4.3 Risk: Accessibility Regression
- **Mitigation:** Maintain ARIA attributes
- **Mitigation:** Test keyboard navigation
- **Mitigation:** Ensure color contrast remains sufficient

### 4.4 Risk: Data Inconsistency
- **Mitigation:** Keep static JSON as single source of truth
- **Mitigation:** Validate JSON structure before use
- **Mitigation:** Add runtime type checks

### 4.5 Risk: Environment Limitations
- **Mitigation:** Document loopback restriction clearly
- **Mitigation:** Provide manual verification steps
- **Mitigation:** Design for graceful degradation

---

## 5. Verification Plan

### 5.1 Pre-Implementation Baseline
- [x] Backend tests: 98 passed, 5 warnings
- [x] Frontend build: Successful
- [x] Frontend tests: 5 passed
- [x] TypeScript compilation: Successful
- [x] Linting: Passed

### 5.2 Post-Implementation Verification
- [ ] Backend tests: Must pass (98+ tests)
- [ ] Frontend build: Must succeed
- [ ] Frontend tests: Must pass (5+ tests)
- [ ] TypeScript compilation: Must succeed
- [ ] Linting: Must pass
- [ ] Manual testing: All 8 views functional
- [ ] Accessibility: Keyboard navigation works
- [ ] Responsive: Mobile layout works

### 5.3 Regression Checks
- [ ] API contract unchanged (`/v1/score` still returns `not_validated`)
- [ ] Dataset inventory unchanged (no new datasets fabricated)
- [ ] Historical benchmark metrics unchanged
- [ ] Phase 1-5 reports unchanged (hash verification)

### 5.4 Manual Verification Steps
1. Start frontend: `cd frontend && node node_modules/vite/bin/vite.js`
2. Navigate to all 8 views
3. Test search/filter in Data Discovery
4. Test dataset detail view
5. Test experiment comparison in Model Lab
6. Test keyboard navigation
7. Test responsive layout (resize browser)
8. Verify empty states display correctly
9. Verify error states display correctly
10. Verify loading states display correctly

---

## 6. Implementation Order

### Phase 6.2.1: UI/UX Improvements (Week 1)
1. Enhanced navigation (breadcrumbs, keyboard shortcuts)
2. Improved empty states (context-specific)
3. Enhanced loading states (skeleton loaders)
4. Enhanced error states (retry buttons, details)

### Phase 6.2.2: Data Discovery Enhancements (Week 1-2)
5. Advanced search and filtering
6. Dataset detail view
7. Qualification workflow visualization

### Phase 6.2.3: Model Lab Enhancements (Week 2)
8. Experiment comparison table
9. Metric visualization
10. Dataset/Target context enhancement

### Phase 6.2.4: Documentation and Testing (Week 2)
11. Update frontend README
12. Create monitoring design document
13. Create explainability design document
14. Run full test suite
15. Manual verification
16. Final report

---

## 7. Success Criteria

### 7.1 Must Have
- [ ] All 8 views render without errors
- [ ] Search/filter works in Data Discovery
- [ ] Dataset detail view displays correctly
- [ ] Experiment comparison works in Model Lab
- [ ] All tests pass (backend + frontend)
- [ ] Production build succeeds
- [ ] API contract unchanged
- [ ] No new datasets fabricated
- [ ] Accessibility maintained
- [ ] Responsive layout works

### 7.2 Should Have
- [ ] Keyboard shortcuts work
- [ ] Breadcrumb navigation works
- [ ] Skeleton loaders display
- [ ] Retry buttons work
- [ ] Metric charts render correctly
- [ ] Qualification workflow visualizes correctly

### 7.3 Nice to Have
- [ ] Saved filters
- [ ] Export functionality
- [ ] Print-friendly views
- [ ] Dark/light mode toggle

---

## 8. Known Blockers

### 8.1 Environment Blockers
- Loopback restriction prevents live API testing
- Cannot verify browser preview in current environment
- Manual verification required for UI testing

### 8.2 Data Blockers
- No authorized Indian borrower dataset
- No real monitoring data
- No SHAP/explainability artifacts
- No multiple experiments for comparison (only LendingClub benchmark)

### 8.3 Technical Blockers
- No backend research endpoints (deferred)
- No automated UI tests (deferred)
- No real-time data refresh (deferred)

---

## 9. Next Steps

1. Implement UI/UX improvements (Priority 1)
2. Implement data discovery enhancements (Priority 2)
3. Implement model lab enhancements (Priority 3)
4. Create design documents for monitoring/explainability (Priority 5)
5. Run full test suite
6. Manual verification
7. Create final report

**Estimated Timeline:** 2 weeks
**Risk Level:** Medium (mostly frontend changes, low risk to backend)
**Dependencies:** None (can proceed with existing data)

---

*End of Phase 6.2 Implementation Plan*
