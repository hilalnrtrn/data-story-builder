# Data Story Builder Demo Script

## 1. Demo goal

Present Data Story Builder as **grounded, explainable and auditable data storytelling**. In approximately 8–9 minutes, demonstrate how a structured dataset becomes deterministic findings, qualified relationships, an evidence-linked executive story and separately managed hypotheses.

Core message: **the LLM is not the analytics engine**. Python owns analytical truth, .NET owns orchestration and story safety, PostgreSQL owns persisted history, and React presents the resulting contracts.

## 2. Canonical demo records and dataset strategy

### Primary record

- Dataset: `sample-data/sales_demo.xlsx`
- Persisted analysis: `78731820-0de8-4f31-a55e-f1532ab99077`
- Use for Overview, Insights, explainability, Executive Story, passing Story Audit, Hypothesis Tracker and History.
- This is the latest post-fix canonical record. Prefer reopening it from History; do not upload it unless a fresh run is explicitly required and provider use is approved.

### Secondary dirty-data record

- Dataset: `sample-data/sales_demo_dirty.csv`
- Persisted analysis: `a6d93c99-5d61-4e3f-b039-321a8af8310b`
- Use only for the optional data-quality segment.
- Its historical blocked story audit is retained truthfully and must not be regenerated.

### Additional backup record

- Dataset: `sample-data/sales_demo_clean.csv`
- Persisted analysis: `f6c87dfb-8ddd-4e66-aca2-76fa1dbd29d1`
- Use for persisted clean analytical results if necessary, but use the XLSX record for the current passing audit demonstration.

No new demo dataset is needed. Golden Truth and all three sample files remain unchanged.

## 3. Golden demo anchors

Use only verified controlled findings:

| Finding | Verified anchor |
| --- | --- |
| Revenue | 1,000,000 → 1,300,000; +300,000; +30% |
| Orders | 10,000 → 8,500; -15% |
| Customers | 8,000 → 7,040; -12% |
| MarketingSpend | 100,000 → 120,000; +20% |
| Marmara Revenue | 380,000 → 590,000; +210,000; 70% of net Revenue increase |
| Online Revenue | 550,000 → 780,000; +230,000; approximately 76.67% secondary contribution |
| Smart Watch | June Revenue anomaly; one-off risk, not sustained growth |
| Office Chair | persistent upward Revenue trend across 2025 |
| Relationship | MarketingSpend/Revenue `CO_MOVES_WITH` |
| Causality | `CAUSALITY_NOT_ESTABLISHED` |
| Missing context | CompetitorPrice, UnitPrice and PricingChange are unavailable context, not malformed fields |

Do not introduce explanations that are absent from the persisted evidence.

## 4. Pre-demo checklist

- [ ] PostgreSQL is running.
- [ ] `http://127.0.0.1:8000/health` reports analytics healthy.
- [ ] `http://localhost:5056/api/health` reports backend, analytics and database healthy.
- [ ] Frontend is running at `http://localhost:5173`.
- [ ] History contains XLSX analysis `78731820-0de8-4f31-a55e-f1532ab99077`.
- [ ] XLSX status is `Completed` and Overview loads without stale data.
- [ ] XLSX generated story is present in Turkish.
- [ ] Story/Data Diff and Full Story Audit display Pass for the XLSX record.
- [ ] One `OPEN` hypothesis is visible.
- [ ] Browser zoom makes all cards and drawer content readable.
- [ ] Select the intended UI language and theme before presenting.
- [ ] Browser developer console has no errors.
- [ ] `sample-data/sales_demo.xlsx` is ready only if showing file selection; do not submit it.
- [ ] No API key, database password, terminal secret or environment file is visible.
- [ ] Close unrelated tabs, terminals, notifications and windows.
- [ ] Open History and the XLSX record once before the audience arrives to warm the persisted GET path.

## 5. 8–9 minute sequence and talk track

### A. Opening — 0:00–0:35

- **Screen:** Application shell or Overview.
- **Click:** None.
- **Expected:** Data Story Builder workspace and current persisted analysis.
- **Say:** “Data Story Builder turns structured CSV or Excel data into deterministic analytical findings, validated relationships, an auditable executive story and evidence-linked hypotheses. The key boundary is that the LLM is not the analytics engine: it narrates a plan produced from validated findings.”
- **Technical point:** Fact discovery and numerical truth remain deterministic; hypotheses remain separate from facts.
- **Fallback:** If the application is unavailable, show `docs/architecture.md` and continue without inventing UI output.

### B. Dataset and persisted opening — 0:35–1:00

- **Screen:** History, then Overview.
- **Click:** Select `sales_demo.xlsx` with ID ending `...2ab99077`.
- **Expected:** The completed XLSX analysis opens and the workspace returns to Overview.
- **Say:** “I am reopening a completed PostgreSQL record. This is a GET-only path: analytics, story generation and auditing are not rerun.”
- **Technical point:** Persistence-backed restoration and a stable analysis ID across sections.
- **Fallback:** If History cannot load, refresh the already selected XLSX record; do not upload.

### C. Overview and Dataset Health — 1:00–1:55

- **Screen:** Overview.
- **Click:** No navigation; point to KPI cards, charts and Dataset Health.
- **Expected:** 43,800 rows, 14 columns, data-quality profile, persisted charts, 87 insights, 48 relationships and story/hypothesis state.
- **Say:** “Overview summarizes backend-produced results. React formats this contract but does not calculate insights. Revenue rises sharply in June, while regional and metric-change charts provide the analytical context.”
- **Technical point:** Presentation-only frontend and persisted profile/chart contracts.
- **Fallback:** If one chart is unavailable, use the KPI/profile values and state that the component truthfully exposes unavailable persisted data.

### Optional dirty-data insert — 1:55–2:35

- **Screen:** History → `sales_demo_dirty.csv` → Overview/Dataset Health.
- **Click:** Open ID ending `...8af8310b`; return to XLSX afterward.
- **Expected:** 43,810 rows read and 43,800 prepared; 10 duplicates removed, 12 categorical normalizations, 5 whitespace fixes, 50 missing values detected, 2 date-conversion errors and 4 numeric conversions. Integrity retains semantic problems such as negative Orders, invalid Discount range, Returns greater than Quantity and category inconsistency.
- **Say:** “Preparation repairs recoverable representation issues. Integrity does something different: it reports business or semantic invalidity rather than silently hiding it.”
- **Technical point:** Preparation and metric/data-integrity responsibilities are distinct.
- **Fallback:** If time is short or switching risks confusion, omit this insert and mention the persisted dirty record verbally. Never regenerate its historical audit.

### D. Insight Explorer — 1:55–3:05 (or 2:35–3:45 with dirty insert)

- **Screen:** Insights.
- **Click:** Filter/select `CHANGE` Revenue, then one counter-signal and one contribution/anomaly.
- **Expected:** Revenue +30%; Customers -12% or Orders -15%; Marmara contribution or Smart Watch anomaly, with direction, period, confidence, importance and relevance.
- **Say:** “The system does not rank only by the largest percentage. It combines analytical importance, confidence and business relevance while retaining counter-signals.”
- **Technical point:** Deterministic insight types, scoring, ranking and business relevance.
- **Fallback:** Use search/type filters rather than scrolling all 87 findings. If a preferred item is filtered out, clear filters and choose the known ID/type.

### E. Why This Insight? — 3:05–4:15

- **Screen:** Revenue +30% insight detail drawer.
- **Click:** Open **Why This Insight?** for `CHANGE-Revenue-2025-05-2025-06`.
- **Expected:** Previous/current values, +300,000 absolute change, +30% relative change, evidence, calculation, confidence, importance, relevance, relationships, counter-evidence, integrity, causality and missing context where exposed.
- **Say:** “This is the explainability layer. It shows what happened, how it was calculated, why it matters, what weakens the interpretation, and which context is unavailable. The user does not have to trust a headline without its evidence.”
- **Technical point:** Evidence-linked analytical truth; no React-side analytical recomputation.
- **Fallback:** If a subsection has no persisted value, point out the truthful unavailable state rather than filling it with a demo claim.

### F. Causality trap and Missing Context — 4:15–5:05

- **Screen:** Revenue detail relationship/causality and missing-context areas; alternatively MarketingSpend insight detail.
- **Click:** Expand related signals, causality and missing context if collapsed.
- **Expected:** MarketingSpend +20%, Revenue +30%, `CO_MOVES_WITH`, `CAUSALITY_NOT_ESTABLISHED`, plus available pricing/competitor limitations.
- **Say:** “These metrics moved together, but the system does not conclude that marketing spend caused revenue growth. This is observational spreadsheet data. Competitor and pricing context is unavailable, and ‘context unavailable’ is different from ‘bad data.’”
- **Technical point:** Causality Guard and Missing Context prevent unsupported interpretation.
- **Fallback:** If context cards are not visible for the selected item, use the persisted story limitation or another Revenue-related insight that exposes them. Claim only fields actually shown.

### G. Executive Story — 5:05–6:00

- **Screen:** Executive Story.
- **Click:** Select the sidebar story section; expand one claim/evidence trace if useful.
- **Expected:** Turkish title, executive summary, seven structured sections and nine evidence-linked story items.
- **Say:** “The Story Planner selected validated findings first. The provider received bounded structured evidence and turned it into natural language. It did not receive the raw spreadsheet, and each story item remains linked through its SourceItemId.”
- **Technical point:** Planner-before-LLM grounding, generation-language persistence and traceability.
- **Fallback:** If provider services are unavailable, nothing changes here: use the persisted story. If story content is absent, do not fabricate it; explain the persisted generation state.

### H. Story Audit — 6:00–6:55

- **Screen:** Story Audit.
- **Click:** Open summary and one numerical/item audit detail.
- **Expected:** XLSX Story/Data Diff Pass and Full Story Audit Pass; full coverage, no numerical mismatch, causal/semantic safety, narrative-bias result and persisted decision.
- **Say:** “Generated language is not trusted automatically. The application checks source coverage, numerical support, direction and semantic safety, causality, required limitations and narrative framing before persisting the final audit.”
- **Technical point:** Deterministic post-generation verification rather than a second LLM judge.
- **Fallback:** If History accidentally points to old clean/dirty blocked audits, return to XLSX ID `...2ab99077`. Do not regenerate historical records.

### I. Hypothesis Tracker — 6:55–7:50

- **Screen:** Hypotheses.
- **Click:** Open the single MarketingSpend/Revenue hypothesis; do not change status.
- **Expected:** One `OPEN` hypothesis, deterministic confidence, source insights/relationship, supporting and counter-evidence, missing context and `CAUSALITY_NOT_ESTABLISHED`.
- **Say:** “The hypothesis is a possible explanation, not a fact. It was created deterministically from validated signals and can move through OPEN, SUPPORTED, CONFIRMED or REJECTED with a recorded reason. Even CONFIRMED is a lifecycle state; it does not rewrite source facts.”
- **Technical point:** Epistemic separation and constrained persisted lifecycle.
- **Fallback:** If detail is collapsed, show the card status/confidence and describe only the persisted source links visible in the UI.

### J. History, Golden Truth and close — 7:50–8:45

- **Screen:** History, then optionally `docs/architecture.md`.
- **Click:** Open History; point to XLSX/clean/dirty records without selecting another blocked audit.
- **Expected:** Persisted analyses and metadata.
- **Say:** “History is PostgreSQL-backed. Reopening an analysis does not rerun analytics, call the LLM, recreate audits or rediscover hypotheses. Separately, Golden Truth uses a controlled dataset and known expected outcomes in regression tests: ‘the code runs’ is not enough. React presents, .NET orchestrates and persists, Python owns deterministic analytics, the LLM narrates only, and the Story Auditor verifies the result.”
- **Technical point:** Persistence memory, deterministic verification philosophy and final architecture boundary.
- **Fallback:** If History is unavailable, retain the open XLSX view and use the architecture document. Do not upload merely to prove persistence.

## 6. Golden Truth explanation (20–30 seconds)

“Golden Truth connects a controlled scenario to `expected_results.json` and deterministic regression tests. It verifies that known changes, contributions, anomalies, relationships and safety constraints remain correct. It is test-only: it is neither hard-coded frontend data nor runtime prompt input, and it is never sent to the LLM.”

## 7. Architecture closing (30 seconds)

“React is the presentation layer. ASP.NET Core owns the API, lifecycle, persistence coordination and story safety. Python owns deterministic and statistical analytics. PostgreSQL owns persisted analytical history. The LLM is limited to narration of grounded findings, and the Story Auditor independently checks that narration afterward.”

## 8. Failure fallbacks

| Situation | Safe response |
| --- | --- |
| Live upload would consume provider quota | Use persisted XLSX analysis; explain that upload has already been demonstrated by the stored lifecycle. |
| Provider unavailable | Show the persisted generated story and explain the provider boundary. |
| Frontend upload fails | History → XLSX `78731820-0de8-4f31-a55e-f1532ab99077` → continue. |
| Old clean/dirty audit is blocked | Preserve it; switch to latest XLSX for the current passing audit. |
| Analytics/backend unavailable | Do not invent output. Use architecture documentation and previously prepared approved screenshots if available. |
| Preferred insight/detail subsection unavailable | Use another verified persisted item or explain the truthful unavailable state. |
| UI language differs from generated story | Explain that generation language is persisted and UI toggling does not regenerate prose. |

## 9. Rehearsal verification snapshot

Read-only GET verification on 29 August 2026 confirmed the primary record:

| Property | Persisted XLSX value |
| --- | ---: |
| Analysis status | `Completed` |
| Prepared rows | 43,800 |
| Insights | 87 |
| Relationships | 48 |
| Insight integrity evaluations | 87 |
| Causality evaluations | 48 |
| Missing-context evaluations | 87 |
| Story sections | 7 |
| Story items | 9 |
| Story generation | `Succeeded` (`tr`) |
| Story/Data Diff | Pass |
| Full Story Audit | Pass |
| Hypotheses | 1 `OPEN` |

The old clean and dirty records remain `Completed` but retain their historical blocked audit artifacts. That difference is expected and must not be repaired through regeneration during the demo.

## 10. Key messages

- Grounded: numerical truth comes from deterministic/statistical analytics.
- Explainable: important findings expose calculation, evidence and limitations.
- Auditable: generated story items trace to planned source items and post-generation checks.
- Persistent: History reopens PostgreSQL results without recomputation or provider calls.
- Epistemically careful: facts, insights and hypotheses remain distinct; association is not causation.

## 11. What not to claim

Do not claim that:

- AI discovered causality;
- the LLM analyzed the raw dataset;
- a hypothesis is a fact;
- the system performs advanced causal inference;
- the system supports arbitrary unstructured files;
- the MVP is production enterprise SaaS;
- every possible semantic hallucination is theoretically impossible;
- historical audits were regenerated after later fixes;
- preparation silently resolves all semantic integrity problems;
- Golden Truth is runtime data or is sent to the provider.

## 12. Provider safety

This demo plan uses persisted records only:

- Groq calls: **0**
- OpenAI calls: **0**
- Other real LLM calls: **0**
- Analysis POST requests required: **0**
- Hypothesis PATCH requests required: **0**

Do not submit the prepared sample file during rehearsal or presentation unless a fresh provider-backed run is separately justified and explicitly approved.
