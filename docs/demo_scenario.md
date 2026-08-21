# Data Story Builder — Demo Scenario

## 1. Purpose

This dataset is a controlled synthetic dataset created specifically for the
Data Story Builder MVP.

The purpose of the dataset is not to represent a real company or reproduce
real commercial data.

It provides a controlled analytical environment in which expected findings
are known in advance and can later be compared with the outputs produced by
the Data Story Builder analytics pipeline.

The dataset is designed to support validation of:

- Data Preparation
- Data Profiling
- Metric / Data Integrity
- Change Detection
- Trend Detection
- Anomaly Detection
- Contribution Analysis
- Contrast Analysis
- Confidence and Importance Scoring
- Relationship Detection
- Business Relevance
- Insight Integrity
- Counter Evidence Detection
- Outlier Detection
- One-Off Effect Detection
- Data Consistency
- Causality Guard
- Missing Context
- Story Planning
- Story Generation
- Story / Data Diff
- Evidence Coverage
- Narrative Bias Detection
- Story Auditing

---

## 2. Demo Company

### NovaRetail

NovaRetail is a fictional retail company operating across Türkiye.

The company sells products through both online and physical-store channels
in three primary product categories:

- Electronics
- Home
- Office

The purpose of the business scenario is to analyze changes in commercial
performance and determine which developments are significant enough to be
included in an executive data story.

---

## 3. Analysis Period

Start Date:

2025-01-01

End Date:

2025-12-31

Frequency:

Daily

The full-year period provides enough historical observations for:

- period comparisons,
- trend analysis,
- anomaly detection,
- persistence analysis,
- one-off effect detection.

---

## 4. Dataset Grain

Each row represents the daily aggregated performance of one:

Date + Region + Product + Channel

combination.

Primary grain:

Date × Region × Product × Channel

The dataset is not transaction-level data.

---

## 5. Regions

- Marmara
- Ege
- İç Anadolu
- Akdeniz
- Karadeniz

---

## 6. Product Categories and Products

### Electronics

- Wireless Headphones
- Smart Watch
- Bluetooth Speaker
- Power Bank

### Home

- Coffee Machine
- Air Fryer
- Vacuum Cleaner
- Desk Lamp

### Office

- Office Chair
- Mechanical Keyboard
- Monitor Stand
- Webcam

---

## 7. Sales Channels

- Online
- Store

---

## 8. Campaign Values

- None
- Summer Sale
- Back to School
- Black Friday
- Holiday Campaign

The absence of a campaign is represented by `None`, not NULL.

This prevents the legitimate absence of a campaign from being incorrectly
interpreted as missing data.

---

## 9. Primary Metrics

The raw dataset contains:

- Revenue
- Orders
- Customers
- Quantity
- MarketingSpend
- StockLevel
- Discount
- Returns

The analytics layer may also calculate deterministic derived metrics such as:

- AverageOrderValue
- RevenuePerCustomer
- UnitsPerOrder
- ReturnRate

---

## 10. Main Controlled Business Event

The main demo event occurs between May 2025 and June 2025.

Expected company-level results:

| Metric | May 2025 | June 2025 | Expected Change |
|---|---:|---:|---:|
| Revenue | 1,000,000 TRY | 1,300,000 TRY | +30% |
| Orders | 10,000 | 8,500 | -15% |
| Customers | 8,000 | 7,040 | -12% |
| MarketingSpend | 100,000 TRY | 120,000 TRY | +20% |

This event deliberately creates a mixed business signal.

Revenue increases strongly while order and customer volumes decline.

The purpose is to ensure that the system does not interpret Revenue growth
as uniformly positive business performance without examining counter
evidence.

---

## 11. Revenue Contribution Scenario

Revenue by region for May and June:

| Region | May Revenue | June Revenue | Absolute Change |
|---|---:|---:|---:|
| Marmara | 380,000 | 590,000 | +210,000 |
| Ege | 220,000 | 260,000 | +40,000 |
| Akdeniz | 160,000 | 190,000 | +30,000 |
| İç Anadolu | 150,000 | 135,000 | -15,000 |
| Karadeniz | 90,000 | 125,000 | +35,000 |
| Total | 1,000,000 | 1,300,000 | +300,000 |

Marmara therefore contributes:

210,000 / 300,000 = 70%

of the net Revenue increase.

Expected analytical finding:

Marmara is the primary positive contributor to the May-to-June Revenue
increase.

---

## 12. Contrast Scenario

Marmara Revenue changes approximately +55.26% between May and June.

İç Anadolu Revenue changes -10%.

Expected analytical behavior:

The system should detect a meaningful regional contrast between Marmara and
İç Anadolu.

---

## 13. Anomaly and One-Off Scenario

Smart Watch Revenue follows a relatively stable historical pattern before
experiencing a strong spike in June.

The value returns close to its historical range in July.

Expected behavior:

- Anomaly detected
- One-off risk high
- Sustained upward trend not established

---

## 14. Sustained Trend Scenario

Office Chair Revenue increases consistently throughout 2025.

Expected behavior:

- Upward trend detected
- High persistence
- Trend should not depend on a single observation

---

## 15. Outlier Dependency Scenario

Bluetooth Speaker Revenue remains approximately stable during most of the
year but contains a deliberately extreme observation in September.

Expected behavior:

- September outlier detected
- Any apparent strong trend should be identified as highly dependent on the
  outlier
- Reliable sustained growth should not be claimed

---

## 16. Causality Trap

Between May and June:

- MarketingSpend increases approximately 20%
- Revenue increases approximately 30%

The dataset intentionally does not contain evidence that MarketingSpend
caused the Revenue increase.

Expected behavior:

Association or co-movement may be reported.

Causality must not be claimed.

---

## 17. Missing Context

The dataset intentionally does not contain:

- CompetitorPrice
- UnitPrice
- PricingChange

These are not data-quality defects.

They are known context gaps.

For example, Revenue increases while Orders and Customers decline and
AverageOrderValue increases.

The system may observe these facts but must not infer that product prices
increased because unit pricing information is unavailable.

---

## 18. Business Relevance Scenario

A later period contains a controlled deterioration in ReturnRate together
with a numerically larger change in Discount.

The purpose is to test the principle:

Largest numerical change != highest business relevance.

ReturnRate has negative directionality and should be treated as a meaningful
business-risk indicator.

---

## 19. Clean and Dirty Dataset Strategy

Two CSV variants will be generated.

### sales_demo_clean.csv

Contains the canonical controlled analytical dataset.

It is used primarily for analytics and Golden Truth validation.

### sales_demo_dirty.csv

Derived from the clean dataset.

It contains deliberately inserted data-quality problems including:

- duplicate rows,
- categorical formatting inconsistencies,
- whitespace inconsistencies,
- invalid Product-Category mappings,
- missing StockLevel values,
- invalid Discount values,
- negative Orders,
- Returns greater than Quantity,
- invalid Date values,
- numeric format inconsistencies.

The dirty dataset is used primarily to test Data Preparation, Data Profiling,
and Metric/Data Integrity.

---

## 20. Golden Truth Principle

The expected analytical results are defined independently from the analytics
implementation.

The analytics engine must not contain hard-coded logic such as:

- special handling for June 2025,
- special handling for Marmara,
- special handling for Smart Watch,
- hard-coded expected percentage changes.

The controlled dataset exists to test the algorithms.

The algorithms must remain reusable for newly uploaded datasets that follow
the supported analytical contract.

---

## 21. LLM Boundary

The LLM will not analyze the raw dataset.

The LLM will not calculate metrics, discover insights, determine
relationships, assign analytical scores, or infer unsupported causes.

The intended flow is:

Raw Data
→ Deterministic / Statistical Analytics
→ Validated Structured Findings
→ Story Planner
→ LLM Narrative
→ Story Auditor

The final narrative must therefore be grounded in validated analytical
findings rather than generated directly from the raw Excel or CSV file.