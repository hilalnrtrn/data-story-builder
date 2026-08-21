# Data Story Builder — Data Dictionary

## 1. Purpose

This document defines the analytical contract of the controlled NovaRetail demo dataset used by the Data Story Builder MVP.

The purpose of the data dictionary is to describe:

* what each column represents,
* whether it is a metric, dimension, or temporal field,
* how metrics may be aggregated,
* which values are considered valid,
* whether NULL or negative values are allowed,
* how a metric should generally be interpreted from a business perspective,
* which analytical components may use the field.

The data dictionary is intended to support:

* Data Preparation,
* Data Profiling,
* Metric / Data Integrity,
* Insight Detection,
* Business Relevance,
* Missing Context detection,
* explainability.

---

# 2. Dataset Identity

**Dataset Name:** NovaRetail Sales Performance

**Dataset Type:** Controlled synthetic analytical dataset

**Analysis Period:** 2025-01-01 → 2025-12-31

**Frequency:** Daily

**Primary Grain:**

`Date × Region × Product × Channel`

Each row represents the daily aggregated performance of one product in one region through one sales channel.

The dataset is not transaction-level data.

---

# 3. Column Overview

| Column         | Role               | Data Type | Metric Type |
| -------------- | ------------------ | --------- | ----------- |
| Date           | Temporal Dimension | Date      | N/A         |
| Region         | Dimension          | String    | N/A         |
| Category       | Dimension          | String    | N/A         |
| Product        | Dimension          | String    | N/A         |
| Channel        | Dimension          | String    | N/A         |
| Campaign       | Dimension          | String    | N/A         |
| Revenue        | Metric             | Decimal   | Additive    |
| Orders         | Metric             | Integer   | Additive    |
| Customers      | Metric             | Integer   | Additive*   |
| Quantity       | Metric             | Integer   | Additive    |
| MarketingSpend | Metric             | Decimal   | Additive    |
| StockLevel     | Metric             | Integer   | Snapshot    |
| Discount       | Metric             | Decimal   | Ratio       |
| Returns        | Metric             | Integer   | Additive    |

---

# 4. Dimension Definitions

## 4.1 Date

**Role:** Temporal Dimension
**Data Type:** Date
**Format:** `YYYY-MM-DD`
**Unit:** Day
**Aggregation:** Not applicable
**Nullable:** No
**Negative Allowed:** Not applicable
**Valid Range:** 2025-01-01 → 2025-12-31

**Business Meaning**

The calendar date to which the aggregated sales observation belongs.

**Analytics Usage**

* Period Comparison
* Change Detection
* Trend Detection
* Anomaly Detection
* Persistence Analysis
* One-Off Effect Detection
* Temporal Relationships

---

## 4.2 Region

**Role:** Dimension
**Data Type:** Categorical String
**Aggregation:** GROUP BY
**Nullable:** No

**Valid Values**

* Marmara
* Ege
* İç Anadolu
* Akdeniz
* Karadeniz

**Business Meaning**

The geographical sales region associated with the observation.

**Analytics Usage**

* Contribution Analysis
* Contrast Analysis
* Regional Drill-down
* Relationship Detection
* Business Relevance

**Consistency Requirement**

Values should be normalized to the canonical representation defined above.

For example:

`MARMARA`, `marmara`, and `Marmara ` should normalize to:

`Marmara`

---

## 4.3 Category

**Role:** Dimension
**Data Type:** Categorical String
**Aggregation:** GROUP BY
**Nullable:** No

**Valid Values**

* Electronics
* Home
* Office

**Business Meaning**

The primary product category to which the product belongs.

**Analytics Usage**

* Contribution Analysis
* Contrast Analysis
* Category Drill-down
* Data Consistency

**Consistency Rule**

Each product must always belong to its predefined category.

---

## 4.4 Product

**Role:** Dimension
**Data Type:** Categorical String
**Aggregation:** GROUP BY
**Nullable:** No

**Valid Values**

### Electronics

* Wireless Headphones
* Smart Watch
* Bluetooth Speaker
* Power Bank

### Home

* Coffee Machine
* Air Fryer
* Vacuum Cleaner
* Desk Lamp

### Office

* Office Chair
* Mechanical Keyboard
* Monitor Stand
* Webcam

**Expected Cardinality:** 12

**Business Meaning**

The product whose aggregated performance is represented by the row.

**Analytics Usage**

* Change Detection
* Trend Detection
* Anomaly Detection
* Contribution Analysis
* Contrast Analysis
* Product Drill-down
* Integrity Checks

---

## 4.5 Channel

**Role:** Dimension
**Data Type:** Categorical String
**Aggregation:** GROUP BY
**Nullable:** No

**Valid Values**

* Online
* Store

**Business Meaning**

The sales channel through which the observed performance occurred.

**Analytics Usage**

* Contribution Analysis
* Contrast Analysis
* Relationship Detection

---

## 4.6 Campaign

**Role:** Dimension
**Data Type:** Categorical String
**Aggregation:** GROUP BY
**Nullable:** No

**Valid Values**

* None
* Summer Sale
* Back to School
* Black Friday
* Holiday Campaign

**Business Meaning**

The campaign active for the observation.

`None` represents the legitimate absence of a campaign.

It must not be interpreted as missing data.

**Analytics Usage**

* Context
* Relationship Detection
* Contrast Analysis
* Causality Guard

---

# 5. Metric Definitions

## 5.1 Revenue

**Role:** Metric
**Metric Type:** Additive
**Data Type:** Decimal
**Unit:** TRY
**Aggregation:** SUM
**Nullable:** No
**Negative Allowed:** No
**Valid Range:** `Revenue >= 0`
**Directionality:** HIGHER_IS_BETTER
**Business Priority:** 0.95

**Business Meaning**

Gross sales revenue generated by the corresponding grain.

**Analytics Usage**

* Change Detection
* Trend Detection
* Anomaly Detection
* Contribution Analysis
* Contrast Analysis
* Relationship Detection
* Importance Scoring
* Business Relevance
* Counter Evidence
* Story Planning

**Demo Role**

Revenue is the primary business KPI of the controlled demo scenario.

---

## 5.2 Orders

**Role:** Metric
**Metric Type:** Additive
**Data Type:** Integer
**Unit:** Orders
**Aggregation:** SUM
**Nullable:** No
**Negative Allowed:** No
**Valid Range:** `Orders >= 0`
**Directionality:** HIGHER_IS_BETTER
**Business Priority:** 0.85

**Business Meaning**

Number of orders represented by the corresponding grain.

**Analytics Usage**

* Change Detection
* Trend Detection
* Relationship Detection
* Counter Evidence
* Derived Metrics

**Demo Role**

Orders intentionally decline during the main May-to-June Revenue growth event.

---

## 5.3 Customers

**Role:** Metric
**Metric Type:** Additive under controlled demo assumption
**Data Type:** Integer
**Unit:** Customers
**Aggregation:** SUM*
**Nullable:** No
**Negative Allowed:** No
**Valid Range:** `Customers >= 0`
**Directionality:** HIGHER_IS_BETTER
**Business Priority:** 0.90

**Business Meaning**

Non-overlapping purchasing customer count assigned to the corresponding grain.

**Important Aggregation Assumption**

In real business datasets, unique customer counts are generally non-additive because the same customer may appear in multiple groups.

For this controlled synthetic dataset, customer populations are assumed to be non-overlapping across generated grain rows so that SUM aggregation remains valid.

This assumption applies only to the controlled demo dataset.

**Analytics Usage**

* Change Detection
* Relationship Detection
* Counter Evidence
* Derived Metrics
* Business Relevance

---

## 5.4 Quantity

**Role:** Metric
**Metric Type:** Additive
**Data Type:** Integer
**Unit:** Units
**Aggregation:** SUM
**Nullable:** No
**Negative Allowed:** No
**Valid Range:** `Quantity >= 0`
**Directionality:** HIGHER_IS_BETTER
**Business Priority:** 0.70

**Business Meaning**

Total number of product units sold within the corresponding grain.

**Analytics Usage**

* Change Detection
* Trend Detection
* Relationship Detection
* Derived Metrics
* Integrity Checks

---

## 5.5 MarketingSpend

**Role:** Metric
**Metric Type:** Additive
**Data Type:** Decimal
**Unit:** TRY
**Aggregation:** SUM
**Nullable:** No
**Negative Allowed:** No
**Valid Range:** `MarketingSpend >= 0`
**Directionality:** CONTEXT_DEPENDENT
**Business Priority:** 0.60

**Business Meaning**

Marketing expenditure allocated to the corresponding grain.

**Analytics Usage**

* Change Detection
* Relationship Detection
* Causality Guard
* Contextual Analysis

**Interpretation Constraint**

An increase in MarketingSpend is not automatically positive or negative.

Co-movement between MarketingSpend and Revenue does not establish causality.

---

## 5.6 StockLevel

**Role:** Metric
**Metric Type:** Snapshot
**Data Type:** Integer
**Unit:** Units
**Aggregation:** LAST or AVG depending on analysis
**Nullable:** Yes
**Negative Allowed:** No
**Valid Range:** `StockLevel >= 0`
**Directionality:** CONTEXT_DEPENDENT
**Business Priority:** 0.65

**Business Meaning**

Available stock level measured at the end of the observation period.

**Important Aggregation Rule**

StockLevel must not normally be aggregated using SUM across time.

For example:

Monday StockLevel = 100
Tuesday StockLevel = 80

does not imply:

Total StockLevel = 180.

Depending on the analysis, the latest value or an average may be appropriate.

**Analytics Usage**

* Data Profiling
* Metric Integrity
* Missing Data Detection
* Context Analysis

---

## 5.7 Discount

**Role:** Metric
**Metric Type:** Ratio
**Data Type:** Decimal
**Unit:** Ratio
**Aggregation:** AVG for MVP analytical use
**Nullable:** No
**Negative Allowed:** No
**Valid Range:** `0.00 <= Discount <= 0.50`
**Directionality:** CONTEXT_DEPENDENT
**Business Priority:** 0.55

**Business Meaning**

Average discount rate applied within the corresponding grain.

Examples:

`0.10 = 10%`

`0.25 = 25%`

**Analytics Usage**

* Relationship Detection
* Context Analysis
* Contrast Analysis
* Business Relevance
* Causality Guard

**Interpretation Constraint**

Discount changes must not automatically be interpreted as the cause of Revenue changes.

---

## 5.8 Returns

**Role:** Metric
**Metric Type:** Additive
**Data Type:** Integer
**Unit:** Units
**Aggregation:** SUM
**Nullable:** No
**Negative Allowed:** No
**Valid Range:** `0 <= Returns <= Quantity`
**Directionality:** LOWER_IS_BETTER
**Business Priority:** 0.85

**Business Meaning**

Number of sold units returned within the corresponding grain.

**Analytics Usage**

* Change Detection
* Business Relevance
* Data Integrity
* Derived Metrics
* Counter Signals

**Business Rule**

Returns must never exceed Quantity.

---

# 6. Derived Metrics

Derived metrics are not stored as mandatory raw dataset columns.

They are calculated deterministically by the analytics layer.

---

## 6.1 AverageOrderValue

**Formula**

`AverageOrderValue = Revenue / Orders`

**Unit:** TRY / Order
**Directionality:** CONTEXT_DEPENDENT

**Aggregation Rule**

Existing row-level AverageOrderValue values must not simply be summed or averaged for higher-level analysis.

The metric should be recalculated using:

`SUM(Revenue) / SUM(Orders)`

for the requested aggregation scope.

**Purpose**

Helps describe situations where Revenue changes differently from order volume.

---

## 6.2 RevenuePerCustomer

**Formula**

`RevenuePerCustomer = Revenue / Customers`

**Unit:** TRY / Customer
**Directionality:** CONTEXT_DEPENDENT

**Aggregation Rule**

Recalculate from aggregated Revenue and Customers rather than averaging precomputed row ratios.

---

## 6.3 UnitsPerOrder

**Formula**

`UnitsPerOrder = Quantity / Orders`

**Unit:** Units / Order
**Directionality:** CONTEXT_DEPENDENT

**Aggregation Rule**

Use:

`SUM(Quantity) / SUM(Orders)`

for higher aggregation levels.

---

## 6.4 ReturnRate

**Formula**

`ReturnRate = Returns / Quantity`

**Unit:** Ratio
**Directionality:** LOWER_IS_BETTER

**Aggregation Rule**

Use:

`SUM(Returns) / SUM(Quantity)`

rather than averaging row-level return rates.

**Business Meaning**

Share of sold units that were returned.

**Business Relevance**

An increase in ReturnRate represents a negative business signal in the NovaRetail demo scenario.

---

# 7. Metric Classification

## Additive Metrics

These metrics may generally be summed across compatible grain rows:

* Revenue
* Orders
* Customers*
* Quantity
* MarketingSpend
* Returns

`Customers` is additive only because of the explicit controlled demo assumption described earlier.

---

## Snapshot Metrics

* StockLevel

Snapshot metrics must not automatically use SUM aggregation across time.

---

## Ratio Metrics

* Discount

---

## Derived Ratio Metrics

* AverageOrderValue
* RevenuePerCustomer
* UnitsPerOrder
* ReturnRate

Derived ratios should be recomputed from their underlying additive components when aggregation level changes.

---

# 8. Business Directionality

Directionality describes the general interpretation of metric movement.

| Metric             | Directionality    |
| ------------------ | ----------------- |
| Revenue            | HIGHER_IS_BETTER  |
| Orders             | HIGHER_IS_BETTER  |
| Customers          | HIGHER_IS_BETTER  |
| Quantity           | HIGHER_IS_BETTER  |
| MarketingSpend     | CONTEXT_DEPENDENT |
| StockLevel         | CONTEXT_DEPENDENT |
| Discount           | CONTEXT_DEPENDENT |
| Returns            | LOWER_IS_BETTER   |
| AverageOrderValue  | CONTEXT_DEPENDENT |
| RevenuePerCustomer | CONTEXT_DEPENDENT |
| UnitsPerOrder      | CONTEXT_DEPENDENT |
| ReturnRate         | LOWER_IS_BETTER   |

Directionality does not by itself determine final Business Relevance.

---

# 9. Business Priority Metadata

Business Priority represents controlled NovaRetail demo metadata.

It is not a universal or scientifically established score.

| Metric         | Business Priority |
| -------------- | ----------------: |
| Revenue        |              0.95 |
| Customers      |              0.90 |
| Orders         |              0.85 |
| Returns        |              0.85 |
| Quantity       |              0.70 |
| StockLevel     |              0.65 |
| MarketingSpend |              0.60 |
| Discount       |              0.55 |

These values may later be used as one input to the Business Relevance layer.

Final Business Relevance must not be equal to Business Priority alone.

---

# 10. Core Data Integrity Rules

The following rules describe expected valid data.

## Numeric Rules

`Revenue >= 0`

`Orders >= 0`

`Customers >= 0`

`Quantity >= 0`

`MarketingSpend >= 0`

`StockLevel >= 0` when present

`Returns >= 0`

---

## Cross-Metric Rules

`Returns <= Quantity`

---

## Discount Rule

`0.00 <= Discount <= 0.50`

---

## Temporal Rule

`2025-01-01 <= Date <= 2025-12-31`

---

## Region Rule

Region must be one of:

* Marmara
* Ege
* İç Anadolu
* Akdeniz
* Karadeniz

---

## Channel Rule

Channel must be one of:

* Online
* Store

---

## Campaign Rule

Campaign must be one of:

* None
* Summer Sale
* Back to School
* Black Friday
* Holiday Campaign

---

# 11. Product-Category Mapping

The following mappings are canonical.

| Product             | Category    |
| ------------------- | ----------- |
| Wireless Headphones | Electronics |
| Smart Watch         | Electronics |
| Bluetooth Speaker   | Electronics |
| Power Bank          | Electronics |
| Coffee Machine      | Home        |
| Air Fryer           | Home        |
| Vacuum Cleaner      | Home        |
| Desk Lamp           | Home        |
| Office Chair        | Office      |
| Mechanical Keyboard | Office      |
| Monitor Stand       | Office      |
| Webcam              | Office      |

Any conflicting Product → Category mapping should be treated as a data-consistency issue.

The system should prefer flagging ambiguous or inconsistent semantic mappings rather than silently inventing a correction.

---

# 12. Known Missing Context

The following fields are deliberately absent from the controlled dataset.

Their absence is not a data-quality error.

They represent known analytical context gaps.

## CompetitorPrice

**Status:** NOT_AVAILABLE

**Why it matters**

Competitor pricing may affect the interpretation of Revenue changes.

The dataset cannot determine whether external competitor pricing influenced observed performance.

---

## UnitPrice

**Status:** NOT_AVAILABLE

**Why it matters**

The dataset contains Revenue, Quantity, Orders, and Customers but does not contain explicit per-unit selling price information.

A rise in Revenue per order must not automatically be interpreted as evidence of a price increase.

---

## PricingChange

**Status:** NOT_AVAILABLE

**Why it matters**

No explicit information is available describing whether NovaRetail changed its pricing policy during the analyzed period.

---

# 13. Missing Data vs Missing Context

These concepts must remain separate.

## Missing Data

A defined dataset field exists but one or more observations are missing.

Example:

`StockLevel = NULL`

This is a Data Quality / Data Integrity issue.

## Missing Context

Information potentially useful for interpreting an insight does not exist in the dataset at all.

Example:

`CompetitorPrice`

This is a context limitation, not a malformed data value.

---

# 14. Causality Interpretation Rule

The dataset may support descriptive, comparative, and correlational observations.

For example:

* Revenue increased.
* Marmara contributed to total Revenue growth.
* MarketingSpend and Revenue increased during the same period.

The dataset does not, by itself, establish causal relationships.

Without additional causal evidence, the system must not state:

* MarketingSpend caused Revenue growth.
* Discount caused Revenue growth.
* A campaign caused increased Orders.
* Higher prices caused higher Revenue.

---

# 15. Aggregation Integrity Principle

Numeric columns must not automatically be treated as additive metrics.

The aggregation rule defined in this data dictionary must be respected.

Examples:

**Valid**

`SUM(Revenue)`

`SUM(Orders)`

`SUM(Quantity)`

**Not generally valid**

`SUM(StockLevel)`

`SUM(Discount)`

`SUM(AverageOrderValue)`

Correct aggregation semantics are part of Metric / Data Integrity.

---

# 16. Golden Dataset Principle

This data dictionary defines the analytical meaning of the controlled dataset.

Analytics code must remain generic and must not contain special-case logic such as:

`if Region == "Marmara"`

`if Product == "Smart Watch"`

`if month == "2025-06"`

These entities are present because they form part of the controlled Golden Truth scenario.

They must be discovered through generic deterministic and statistical analytical rules.

---

# 17. LLM Boundary

The LLM must not independently reinterpret these metric definitions.

Metric semantics, aggregation rules, directionality, data integrity constraints, and derived metric formulas belong to the deterministic analytical layer.

The intended flow remains:

Data Dictionary
→ Data Preparation
→ Data Profiling
→ Metric / Data Integrity
→ Analytics
→ Validated Findings
→ Story Planner
→ LLM
→ Story Auditor

The LLM is responsible for narration, not analytical truth generation.
