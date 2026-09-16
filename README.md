# Infera

Multi-agent research platform. A user asks a research question; Infera runs it
through a fixed pipeline of agents — each backed by a trained model where the
task calls for judgment, and an LLM only where the task is pure language
(phrasing, segmentation) — and returns a consensus-scored report with a
supporting/contradicting evidence graph.

## Pipeline

```
Query Planning        → splits the question into sub-questions (LLM-assisted, rule-based fallback)
Retrieval              → hybrid dense (sentence-transformers + FAISS) + sparse (BM25) search
                          over papers pulled live from Semantic Scholar + arXiv
Ranking                → LightGBM-learned relevance/credibility score over hybrid-search +
                          citation-graph metadata features
Claim Extraction       → atomic claims pulled from top-ranked abstracts (LLM segmentation help)
Verification           → NLI model labels each claim SUPPORTS / REFUTES / NOT_ENOUGH_INFO
                          against its source (SciFact-trainable; see backend/training/train_nli.py)
Stance Clustering      → HDBSCAN over claim embeddings, split by verdict, to surface where
                          sources actually agree/disagree
Consensus/Controversy  → arithmetic aggregation of verdicts per sub-question into an
                          evidence-strength score and a controversy score
Knowledge Graph Builder→ paper + claim nodes; supports / contradicts / cites / extracted_from edges
Report Generation      → LLM drafts prose grounded in the consensus data, then re-runs the
                          same NLI model against its own sentences and asks the LLM to revise
                          any sentence that comes back unsupported
```

**Core principle:** ranking, verification, and consensus scoring are decided by
trained models (a learned ranker, a fine-tuned NLI model, HDBSCAN clustering) —
never by LLM opinion. The LLM's role is scoped to report phrasing and claim
segmentation help; it never scores relevance, credibility, entailment, or
consensus.

**No fabricated data.** Training data is SciFact/FEVER (real, public
fact-verification datasets); live retrieval is real API calls to Semantic
Scholar and arXiv. There are no synthetic papers or invented citations
anywhere in the pipeline.

## Architecture

The orchestrator (`backend/app/orchestrator/`) is hand-built, not a graph
framework: a `ResearchState` dataclass carries every field an agent might read
or write, and `Orchestrator.run()` executes a fixed list of agent callables in
order, tracing each one. This is what lets Report Generation reach back into
Verification's own NLI model to fact-check its own draft — it's just a Python
function call, not orchestrator-level control flow.

```
backend/
  app/
    main.py              FastAPI app, POST /api/research
    config.py             env-driven settings (model names, API keys)
    orchestrator/         ResearchState + the sequential Orchestrator
    agents/                one module per pipeline stage, each a `run(state)` function
    ml/                    NLI wrapper, LightGBM ranker, HDBSCAN clustering
    services/              Semantic Scholar / arXiv clients, hybrid search, scoped LLM client
    models/schemas.py      pydantic models shared by the API and the pipeline
  training/
    train_nli.py           fine-tunes an NLI checkpoint on the real allenai/scifact dataset
    train_ranker.py        trains the LightGBM ranker on real judged (query, paper) data
  tests/

frontend/
  src/
    App.tsx                tabs: report / knowledge graph / sources / claims
    components/             QueryForm, PipelineTrace, ConsensusPanel, ReportView,
                             KnowledgeGraphView (Cytoscape.js), PapersPanel, ClaimsPanel
    lib/api.ts               fetch wrapper for POST /api/research
    types/api.ts              TypeScript mirror of the backend pydantic schemas
```

## Running it

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY (optional — see below)
uvicorn app.main:app --reload --port 8000
```

Without `ANTHROPIC_API_KEY` set, Query Planning, Claim Extraction, and Report
Generation fall back to rule-based/template behavior — the ML-judgment agents
(Retrieval, Ranking, Verification, Stance Clustering, Consensus Scoring, KG
Builder) are unaffected, since they never depend on the LLM.

The NLI model and sentence-transformer embedder download from HuggingFace on
first use. The LightGBM ranker falls back to a transparent fixed-weight linear
score until you train one with `training/train_ranker.py`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Defaults to `http://localhost:8000` for the API; override with `VITE_API_BASE`.

### Tests

```bash
cd backend
pytest
```

## Training the models

**NLI (Verification agent):** `python -m training.train_nli --output_dir ./data/scifact-nli`
fine-tunes a FEVER-pretrained checkpoint on the real `allenai/scifact` dataset
(claim + cited abstract + SUPPORT/CONTRADICT/NOINFO label). Point
`INFERA_NLI_MODEL` at the output directory once trained.

**Ranker (Ranking agent):** `python -m training.train_ranker --source csv
--input judgments.csv` trains on real graded-relevance judgments you supply
(see the script's docstring for the CSV schema). A `--source citation` mode
is also provided as a documented *weak-supervision* fallback — it derives noisy
labels from Semantic Scholar's citation graph and hybrid-search rank, and is
explicitly not a substitute for real judgments.

## Scope

- **Core:** consensus/controversy scoring, paper+claim knowledge graph.
- **Stretch (not implemented):** concept-level entity linking.
- **Out of scope:** research gap detection.

`cites` paper→paper edges are defined in the KG schema but not yet populated —
wiring them up needs an extra Semantic Scholar references/citations call per
paper, deliberately left out of the initial scope.
