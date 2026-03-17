# Sustainable Construction Material Recommendation

AI decision-support tool to recommend eco-friendly and cost-effective construction materials based on structural requirements, lifecycle impact proxies, and sustainability-oriented metrics.

## Problem Statement
Develop an AI decision-support tool that recommends eco-friendly and cost-effective construction materials based on:
1. Structural requirements
2. Lifecycle impact
3. Environmental sustainability metrics

## Our Solution
We built a FastAPI + LangGraph + RAG system with a modern one-page frontend.

### End-to-End Flow
1. User submits structured project inputs from frontend.
2. Backend computes engineering measures and indices.
3. Backend builds one merged `research_query` from user inputs + engineering calculations.
4. Research node runs:
   - RAG retrieval from vector DB (AstraDB + embeddings)
   - Web retrieval via Tavily tool
5. Reporter node merges engineering + RAG + web evidence into a markdown report with chart block.
6. Frontend displays:
   - Short recommendation
   - Full report (markdown rendered)
   - Optional research notes
   - PDF download of on-screen report section

## Implementation Coverage vs Problem Statement

| Requirement | Status | What is implemented |
|---|---|---|
| Structural requirements | Implemented | Floors, building type, timeline, rainfall, budget, priority are converted into engineering scores and indices in `material_feature.py`. |
| Cost-effectiveness | Implemented | Cost sensitivity score, tradeoff adjustment, budget pressure index, and cost-aware recommendation logic in prompts/reporting flow. |
| Environmental sustainability metrics | Implemented | Sustainability weight and eco-priority index; report prompt enforces sustainability comparison and recommendation rationale. |
| Lifecycle impact analysis | Partially Implemented | Current system uses practical proxies (durability, climate suitability, sustainability indicators) from retrieval; explicit numeric LCA engine is not yet implemented. |
| AI recommendation engine | Implemented | Multi-agent workflow (Researcher + Reporter) with merged query retrieval and final report generation. |
| Retrieval quality | Implemented | Shared merged query used for both RAG and web retrieval; retrieval debug added (`top_terms`, `query_preview`). |
| User-facing usability | Implemented | One-page horizontal UI, short recommendation, markdown report rendering, research foldout, and PDF export. |

Estimated completion against statement intent: **~80-85%** (major core features implemented; explicit LCA database modeling remains the biggest gap).

## Key Technical Components

1. Backend API:
   - `POST /api/analyze` in `main.py`
   - Accepts structured fields: building type, floors, location, budget, priority, rainfall, material tone, timeline, tradeoff, notes

2. Engineering module:
   - `backend/workflow/material_feature.py`
   - Computes:
     - `structural_requirement`
     - `cost_sensitivity`
     - `rainfall_risk`
     - `speed_requirement`
     - `thermal_weight`, `cost_weight`, `sustainability_weight`
     - `engineering_indices` (thermal/budget/eco/constructability)

3. RAG module:
   - `backend/workflow/rag.py`
   - AstraDB vector retrieval + Gemini response layer
   - Uses merged query + project context

4. Agent orchestration:
   - `backend/workflow/agents.py` (LangGraph)
   - Research node combines RAG + web evidence
   - Reporter node generates final markdown decision report

5. Prompting:
   - `backend/workflow/prompts/prompts.json`
   - Research and report prompts updated for merged-query grounding and engineering-aware reporting

6. Frontend:
   - `frontend/templates/index.html`
   - `frontend/static/js/main.js`
   - `frontend/static/css/style.css`
   - Includes markdown rendering (`marked`) and PDF export (`html2pdf.js`)

## Issues We Identified and Tackled

1. Windows path escape bug in knowledgebase loader:
   - Fixed invalid backslash path handling using `pathlib` in `knowledgebase.py`.

2. Frontend-backend payload mismatch:
   - Initially frontend sent only `requirement`.
   - Fixed to send structured fields required for engineering calculations.

3. Endpoint and static asset alignment:
   - Corrected frontend to use mounted static routes and API route.

4. Retrieval quality gap:
   - Added merged `research_query` generation from user input + engineering context.
   - Reused same query for RAG and web research.

5. Report quality gap:
   - Updated prompts so report explicitly uses engineering calculations and merged retrieval intent.

6. Explainability gap:
   - Added retrieval debugging to API response:
     - `retrieval_debug.top_terms`
     - `retrieval_debug.query_preview`

## Current API Response (important fields)

- `report`: final markdown recommendation
- `engineering_measures`: computed engineering metrics
- `research_query`: merged retrieval query
- `retrieval_debug`: top terms + query preview
- `rag_data`, `web_data`, `research_data`: traceability outputs

## Setup and Run

1. Install dependencies (project uses `pyproject.toml`).
2. Configure `.env` for keys:
   - `GOOGLE_API_KEY`
   - `Tavily_api_key`
   - `ASTRA_DB_API_ENDPOINT`
   - `ASTRA_DB_APPLICATION_TOKEN`
   - `ASTRA_DB_KEYSPACE` (if used)
3. Run app:
```bash
python main.py
```
4. Open:
```text
http://127.0.0.1:8000
```

## What Remains for a “Perfect” Version

1. Add explicit lifecycle/LCA computation layer (embodied carbon, operational carbon, end-of-life scenarios with numeric model).
2. Add calibrated regional cost database (city/state supplier ranges).
3. Add confidence scoring and citation extraction in final report.
4. Add automated tests for:
   - Engineering score validity
   - Prompt-contract consistency
   - API schema and failure paths

## Final Note
This project already delivers a functional AI decision-support pipeline with engineering-aware recommendations, dual retrieval (RAG + web), and production-style user reporting. The main next maturity step is rigorous quantitative lifecycle modeling.
