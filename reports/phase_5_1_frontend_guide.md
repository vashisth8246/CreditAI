# CreditAI Phase 5.1 — Frontend Guide

**Date:** 13 October 2026
**Frontend:** React + TypeScript + Vite
**Purpose:** Mentor demonstration of CreditAI infrastructure

---

## Overview

The CreditAI frontend is a professional demonstration interface that showcases the implemented ML infrastructure for credit risk assessment. It is designed for mentor presentations and clearly communicates:

- The current state of the system (research prototype, not production)
- Implemented capabilities (data validation, temporal audit, evaluation metrics)
- Current blockers (no authorized Indian dataset, scoring not validated)
- Realistic roadmap for production deployment

**Important:** The frontend does not fabricate results or imply validated model performance. It clearly states that no Indian borrower model has been validated.

---

## Setup Instructions

### Prerequisites

- Node.js 18+ installed
- npm or yarn package manager

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. (Optional) Configure API URL:
```bash
cp .env.example .env
# Edit .env to set VITE_API_BASE_URL if needed
```

### Running the Development Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` (or the port shown in the terminal).

### Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

### Previewing Production Build

```bash
npm run preview
```

---

## Screen Descriptions

### 1. Overview Dashboard

**Purpose:** High-level status of the CreditAI system

**Key Elements:**
- **Model Status:** Shows "NOT VALIDATED" - no validated model exists
- **Backend Health:** Check button to test API connectivity (calls `/health`)
- **Data Qualification:** Shows "No Dataset Qualified" - no authorized dataset in workspace
- **Implemented Capabilities:** List of all Phase 5 infrastructure components
- **Current Blockers:** Clear statement of what prevents production use
- **Next Milestones:** Realistic steps toward production deployment
- **Disclaimer:** Explicit statement about research-stage status

**Data Integration:**
- Backend health check calls the real API `/health` endpoint
- Uses `VITE_API_BASE_URL` environment variable (defaults to `http://127.0.0.1:8000`)

### 2. Data Readiness

**Purpose:** Demonstrate the data qualification infrastructure

**Key Elements:**
- **Demo Notice:** Clearly labeled "DEMO DATA — NOT A REAL DATASET"
- **Synthetic Dataset Example:** Shows a qualified synthetic dataset with all metadata fields
- **How Data Readiness Works:** Step-by-step explanation of the qualification process

**Data Integration:**
- Uses synthetic demo data only - no real borrower data
- Demonstrates the qualification gate workflow without requiring real data

### 3. Risk Scoring

**Purpose:** Demonstrate the API contract and disabled scoring state

**Key Elements:**
- **Scoring Notice:** Clearly labeled "SCORING ENGINE DISABLED"
- **API Configuration:** Shows the configured API base URL
- **Demonstration Request:** Button to submit a synthetic request to the API
- **API Response Display:** Shows the actual response from the backend
- **Response Interpretation:** Explains what each field means
- **Request Schema:** Documents the expected request format

**Data Integration:**
- Calls the real `/v1/score` endpoint with synthetic transaction data
- Displays the actual `not_validated` response from the backend
- Clearly shows that `default_probability` is `null` and `validated_risk_estimate` is `false`

### 4. Evaluation

**Purpose:** Show implemented metrics and historical benchmark results

**Key Elements:**
- **Implemented Metric Utilities:** Grid showing all implemented metrics (ROC-AUC, PR-AUC, Brier, KS, Gini, etc.)
- **Historical Benchmark Results:** LendingClub benchmark results from Phase 2.3
- **Benchmark Notice:** Clearly labeled "HISTORICAL U.S. DATA — NOT INDIAN"
- **Benchmark Limitations:** Lists limitations of the historical benchmark
- **Evaluation Infrastructure:** Shows implemented evaluation components
- **Not Yet Validated on Indian Data:** Explicit statement about missing Indian validation

**Data Integration:**
- Uses static benchmark data from Phase 2.3 reports
- No API calls for this screen
- Clearly distinguishes between U.S. historical data and Indian data requirements

### 5. Architecture and Roadmap

**Purpose:** Show system architecture and realistic deployment path

**Key Elements:**
- **Intended Workflow:** Visual diagram of the credit risk workflow
- **Component Status:** List of all components with implementation status
- **Realistic Roadmap:** Step-by-step plan for production deployment
- **Important Note:** Explicit statement that roadmap is a plan, not completed work

**Data Integration:**
- No API calls
- Static documentation of architecture and roadmap

---

## API Integration

### Environment Variable

The frontend uses `VITE_API_BASE_URL` to configure the backend API URL:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
```

### API Endpoints Used

1. **GET /health**
   - Purpose: Check if the backend API is running
   - Called from: Overview Dashboard
   - Response: `{ "status": "ok", "scoring": "not_validated" }`

2. **POST /v1/score**
   - Purpose: Demonstrate the scoring API contract
   - Called from: Risk Scoring screen
   - Request: Synthetic transaction data
   - Response: `{ "score_status": "not_validated", "default_probability": null, ... }`

### Error Handling

- If the API is unavailable, the frontend shows "Unavailable" status
- If the API returns an error, the error message is displayed
- The frontend gracefully handles API unavailability without crashing

---

## Design Principles

### Professional Fintech Style

- Dark theme with slate/blue color palette
- Clean, modern typography
- Card-based layout with subtle shadows
- Responsive design for mobile and desktop

### Clear Data Readiness

- All demo data is clearly labeled as synthetic
- No real borrower data is displayed
- All screens include appropriate disclaimers

### Disabled Scoring

- The scoring screen explicitly states the engine is disabled
- API responses show `not_validated` status
- No risk probabilities are fabricated

### No Fabricated Metrics

- Historical benchmark results are from actual Phase 2.3 reports
- No Indian borrower performance metrics are shown
- All limitations are clearly documented

---

## Testing the Frontend

### Manual Testing Checklist

1. **Overview Dashboard**
   - [ ] Verify "NOT VALIDATED" status is displayed
   - [ ] Click "Check Health" - should show API status
   - [ ] Verify all implemented capabilities are listed
   - [ ] Verify blockers and milestones are displayed
   - [ ] Verify disclaimer is visible

2. **Data Readiness**
   - [ ] Verify "DEMO DATA" notice is displayed
   - [ ] Verify synthetic dataset example is shown
   - [ ] Verify qualification steps are explained

3. **Risk Scoring**
   - [ ] Verify "SCORING ENGINE DISABLED" notice is displayed
   - [ ] Verify API base URL is shown
   - [ ] Click "Submit Demo Request"
   - [ ] Verify response shows `not_validated` status
   - [ ] Verify `default_probability` is `null`
   - [ ] Verify interpretation is displayed

4. **Evaluation**
   - [ ] Verify all implemented metrics are listed
   - [ ] Verify "HISTORICAL U.S. DATA" notice is displayed
   - [ ] Verify benchmark results match Phase 2.3
   - [ ] Verify limitations are listed
   - [ ] Verify "Not Yet Validated" section is displayed

5. **Architecture**
   - [ ] Verify workflow diagram is displayed
   - [ ] Verify component status is accurate
   - [ ] Verify roadmap steps are realistic
   - [ ] Verify important note is displayed

### API Testing

To test with a real backend:

1. Start the backend API:
```bash
cd ..
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

2. Start the frontend:
```bash
cd frontend
npm run dev
```

3. Test the health check and scoring endpoints through the frontend

---

## Files Created/Modified

### Created Files

- `frontend/src/App.tsx` - Main application component with all screens
- `frontend/src/App.css` - Application styles (replaced Vite template)
- `frontend/src/index.css` - Global styles and CSS variables (replaced Vite template)
- `frontend/.env.example` - Environment variable template

### Modified Files

- `frontend/package.json` - Dependencies were installed by Vite (no manual changes)

---

## Mentor Demonstration Guide

### Recommended Demonstration Flow

1. **Start with Overview Dashboard**
   - Explain that CreditAI is a research-stage prototype
   - Show that the model is "NOT VALIDATED"
   - Highlight the implemented capabilities
   - Discuss current blockers (no authorized Indian dataset)

2. **Move to Data Readiness**
   - Explain the data qualification infrastructure
   - Show the synthetic dataset example
   - Walk through the qualification steps
   - Emphasize that real data requires proper authorization

3. **Demonstrate Risk Scoring**
   - Explain that the scoring engine is disabled
   - Show the API configuration
   - Submit a demo request
   - Explain the `not_validated` response
   - Clarify that no risk probability is produced

4. **Show Evaluation**
   - Explain the implemented metrics
   - Show the historical LendingClub benchmark
   - Emphasize that this is U.S. data, not Indian
   - Discuss the limitations of the historical benchmark
   - Explain that Indian validation is still needed

5. **Review Architecture**
   - Show the intended workflow
   - Review component status
   - Walk through the realistic roadmap
   - Emphasize that this is a plan, not completed work

### Key Talking Points

- **Research Stage:** CreditAI is a prototype, not a production system
- **No Indian Data:** No authorized Indian borrower dataset exists in the workspace
- **Infrastructure First:** The focus is on building safe, validated infrastructure
- **Leakage Prevention:** Temporal audit and chronological splits prevent data leakage
- **Transparent Limitations:** All limitations are clearly documented
- **Realistic Roadmap:** Production deployment requires authorization, validation, and regulatory review

### Questions to Anticipate

**Q: Can this be used for real lending decisions?**
A: No. CreditAI is a research-stage prototype. No model has been validated on Indian data. Production deployment requires separate approval, regulatory review, and governance frameworks.

**Q: What performance does it achieve?**
A: The historical LendingClub benchmark achieved ROC-AUC 0.7056 on U.S. data, but this does not establish Indian borrower performance. No Indian borrower model has been validated.

**Q: When will it be ready for production?**
A: Production deployment requires: (1) an authorized Indian repayment dataset, (2) qualification of labels and temporal integrity, (3) leakage-safe chronological baselines, (4) evaluation of calibration and subgroup performance, and (5) separate approval for deployment. Access to data or partner approval has not been secured.

**Q: Can I see real borrower data?**
A: No. The frontend uses only synthetic demo data. No real borrower data is displayed or accessible through this interface.

**Q: Why is the scoring engine disabled?**
A: No validated model exists. The scoring API returns `not_validated` with `default_probability: null` to make this explicit. Scoring should only be enabled after proper validation on authorized data.

---

## Troubleshooting

### Frontend Won't Start

- Ensure Node.js 18+ is installed: `node --version`
- Ensure dependencies are installed: `npm install`
- Check for port conflicts (Vite uses port 5173 by default)

### API Calls Fail

- Ensure the backend API is running on the configured port
- Check the `VITE_API_BASE_URL` environment variable
- Verify the backend is accessible: `curl http://127.0.0.1:8000/health`

### Styles Not Loading

- Ensure `App.css` and `index.css` are imported in `App.tsx` and `main.tsx`
- Clear the browser cache and reload

---

## Security Considerations

- No sensitive data is stored in the frontend
- API calls are made from the browser (CORS must be enabled on the backend)
- Environment variables should not contain secrets
- The frontend is for demonstration only and should not be exposed to the public without proper security review

---

## Future Enhancements

Potential improvements for future phases:

- Add authentication for protected screens
- Implement real-time data qualification status
- Add visualization of evaluation metrics
- Create interactive workflow diagrams
- Add export functionality for reports
- Implement proper error logging and monitoring

---

*End of Frontend Guide*
