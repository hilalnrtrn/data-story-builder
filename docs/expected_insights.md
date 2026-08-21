# Data Story Builder — Expected Insights

## 1. Purpose

This document defines the human-readable Golden Truth expectations for the controlled NovaRetail demo dataset.

The purpose is to describe which analytical findings should be detected when the dataset is processed correctly.

These expectations are defined independently from the analytics implementation.

The analytics engine must discover these findings using generic deterministic or statistical rules.

It must not contain hard-coded conditions for specific dates, regions, products, or expected percentages.

---

# 2. Expectation Categories

Expected findings are divided into three categories.

## REQUIRED

The system is expected to detect these findings.

Failure to detect them indicates that the corresponding analytical capability may not be working correctly.

## ALLOWED

These findings are valid consequences of the controlled dataset and may also be detected.

Their absence does not necessarily indicate failure.

They should not automatically be treated as false positives.

## FORBIDDEN

These are unsupported or analytically invalid conclusions.

The system must not present them as established facts.

Forbidden findings are especially important for:

* Causality Guard
* Missing Context
* Insight Integrity
* Story Auditor

---

# 3. Main Business Event

The primary controlled event occurs between:

**May 2025 → June 2025**

The central business pattern is:

* Revenue increases strongly.
* Orders decline.
* Customers decline.
* MarketingSpend increases.
* Marmara accounts for most of the net Revenue increase.

This event intentionally contains both positive and negative signals.

The expected final interpretation must therefore remain qualified rather than presenting June performance as uniformly positive.

---

# 4. REQUIRED — Revenue Change

**Insight Type:** CHANGE
**Metric:** Revenue
**Previous Period:** May 2025
**Current Period:** June 2025

May Revenue:

`1,000,000 TRY`

June Revenue:

`1,300,000 TRY`

Absolute Change:

`+300,000 TRY`

Percentage Change:

`+30%`

**Expected Direction:** UP

**Required Finding**

Revenue increased by approximately 30% from May to June.

---

# 5. REQUIRED — Orders Change

**Insight Type:** CHANGE
**Metric:** Orders
**Previous Period:** May 2025
**Current Period:** June 2025

May Orders:

`10,000`

June Orders:

`8,500`

Percentage Change:

`-15%`

**Expected Direction:** DOWN

**Required Finding**

Orders decreased by approximately 15% from May to June.

---

# 6. REQUIRED — Customers Change

**Insight Type:** CHANGE
**Metric:** Customers
**Previous Period:** May 2025
**Current Period:** June 2025

May Customers:

`8,000`

June Customers:

`7,040`

Percentage Change:

`-12%`

**Expected Direction:** DOWN

**Required Finding**

Customers decreased by approximately 12% from May to June.

---

# 7. REQUIRED — MarketingSpend Change

**Insight Type:** CHANGE
**Metric:** MarketingSpend
**Previous Period:** May 2025
**Current Period:** June 2025

May MarketingSpend:

`100,000 TRY`

June MarketingSpend:

`120,000 TRY`

Percentage Change:

`+20%`

**Expected Direction:** UP

**Required Finding**

MarketingSpend increased by approximately 20% from May to June.

This finding does not establish that MarketingSpend caused the Revenue increase.

---

# 8. REQUIRED — Average Order Value

AverageOrderValue is a derived metric.

Formula:

`Revenue / Orders`

May:

`1,000,000 / 10,000 = 100 TRY/order`

June:

`1,300,000 / 8,500 ≈ 152.94 TRY/order`

Expected Change:

`≈ +52.94%`

**Required Finding**

AverageOrderValue increased substantially between May and June.

**Interpretation Constraint**

The system must not automatically conclude that product prices increased.

UnitPrice and PricingChange are not available.

---

# 9. REQUIRED — Revenue Per Customer

RevenuePerCustomer is a derived metric.

Formula:

`Revenue / Customers`

May:

`1,000,000 / 8,000 = 125 TRY/customer`

June:

`1,300,000 / 7,040 ≈ 184.66 TRY/customer`

Expected Change:

`≈ +47.73%`

**Required Finding**

RevenuePerCustomer increased substantially between May and June.

This is a mathematical observation.

Its cause is not established by the available dataset.

---

# 10. REQUIRED — Marmara Contribution

Total Revenue Change:

`+300,000 TRY`

Marmara Revenue:

May:

`380,000 TRY`

June:

`590,000 TRY`

Marmara Absolute Change:

`+210,000 TRY`

Contribution to Net Revenue Increase:

`210,000 / 300,000 = 70%`

**Insight Type:** CONTRIBUTION

**Required Finding**

Marmara is the primary positive contributor to the May-to-June Revenue increase and accounts for approximately 70% of the net increase.

---

# 11. REQUIRED — Regional Contrast

Marmara:

`380,000 → 590,000`

Expected Change:

`≈ +55.26%`

İç Anadolu:

`150,000 → 135,000`

Expected Change:

`-10%`

**Insight Type:** CONTRAST

**Required Finding**

Marmara materially outperformed İç Anadolu during the May-to-June period.

This contrast is distinct from Contribution.

Contribution asks:

"Who contributed to the total change?"

Contrast asks:

"Which segments behaved differently?"

---

# 12. REQUIRED — Smart Watch Anomaly

Smart Watch Revenue follows a relatively stable pattern during the months preceding June.

Expected monthly behavior:

| Month     | Revenue |
| --------- | ------: |
| January   |     70K |
| February  |     72K |
| March     |     71K |
| April     |     74K |
| May       |     73K |
| June      |    145K |
| July      |     75K |
| August    |     76K |
| September |     74K |
| October   |     77K |
| November  |     78K |
| December  |     80K |

**Insight Type:** ANOMALY

**Required Findings**

* June should be detected as an unusually high observation.
* The spike should not be interpreted as a reliable sustained upward trend.
* The return toward the historical range in July should support a high one-off risk.

Expected interpretation:

`ANOMALY = TRUE`

`ONE_OFF_RISK = HIGH`

`SUSTAINED_TREND = FALSE`

---

# 13. REQUIRED — Office Chair Trend

Expected monthly Revenue:

| Month     | Revenue |
| --------- | ------: |
| January   |     45K |
| February  |     49K |
| March     |     54K |
| April     |     58K |
| May       |     63K |
| June      |     69K |
| July      |     74K |
| August    |     80K |
| September |     86K |
| October   |     91K |
| November  |     97K |
| December  |    103K |

**Insight Type:** TREND

**Required Findings**

* Direction: UP
* Persistence: HIGH
* The trend should not depend on one isolated observation.
* Month-to-month movement should remain consistently positive.

Expected interpretation:

Office Chair demonstrates sustained Revenue growth across 2025.

---

# 14. REQUIRED — Bluetooth Speaker Outlier Dependency

Bluetooth Speaker should remain relatively stable except for a deliberately extreme September observation.

Expected monthly behavior:

| Month     | Revenue |
| --------- | ------: |
| January   |     50K |
| February  |     51K |
| March     |     50K |
| April     |     52K |
| May       |     51K |
| June      |     52K |
| July      |     51K |
| August    |     53K |
| September |    140K |
| October   |     52K |
| November  |     53K |
| December  |     51K |

**Required Findings**

* September should be treated as an outlier.
* Apparent growth should be highly dependent on the September observation.
* A reliable sustained growth trend must not be established.

Expected Integrity Result:

`OUTLIER = TRUE`

`OUTLIER_DEPENDENCY = HIGH`

`SUSTAINED_TREND = FALSE`

---

# 15. REQUIRED — Counter Evidence

Primary Insight:

Revenue increased approximately 30%.

Required Counter Signals:

* Orders decreased approximately 15%.
* Customers decreased approximately 12%.

The Revenue change itself remains valid.

Expected integrity interpretation:

`PASS_WITH_WARNINGS`

or an equivalent qualified-valid status.

Expected behavior:

The final analytical story must acknowledge the weaker Orders and Customers signals when discussing Revenue growth.

---

# 16. REQUIRED — MarketingSpend / Revenue Relationship

Between May and June:

* MarketingSpend increases approximately 20%.
* Revenue increases approximately 30%.

**Expected Relationship Type:**

`CO_MOVES_WITH`

or an equivalent non-causal association relationship.

**Required Finding**

MarketingSpend and Revenue increased during the same period.

**Required Constraint**

This relationship must not be converted into a causal claim.

---

# 17. REQUIRED — Causality Guard

For the relationship:

`MarketingSpend ↔ Revenue`

Expected status:

`CAUSALITY_NOT_ESTABLISHED`

Acceptable wording includes concepts such as:

* associated with,
* coincided with,
* moved alongside,
* increased during the same period.

Unsupported wording includes:

* caused,
* resulted in,
* led to,
* because of,
* was driven by.

The dataset contains observational co-movement only.

---

# 18. REQUIRED — Missing Context

The following contextual information is intentionally unavailable:

## CompetitorPrice

Expected status:

`NOT_AVAILABLE`

The system must not assume how competitor pricing influenced Revenue.

## UnitPrice

Expected status:

`NOT_AVAILABLE`

The system must not infer that an increase in AverageOrderValue proves that individual selling prices increased.

## PricingChange

Expected status:

`NOT_AVAILABLE`

No explicit pricing-policy change is available in the dataset.

These are context gaps, not malformed data fields.

---

# 19. REQUIRED — Business Relevance Ordering

A later controlled event compares:

* a numerically larger Discount movement,
* a smaller deterioration in ReturnRate.

Expected business behavior:

**ReturnRate deterioration should rank above the Discount movement when the Business Relevance layer evaluates the two findings.**

Reason:

* ReturnRate has negative directionality.
* Returns-related metrics have higher NovaRetail business criticality.
* Discount is context-dependent.
* Largest numerical change is not necessarily the most important business change.

The exact final Business Relevance score is not fixed in Golden Truth.

The required expectation is relative ordering.

---

# 20. ALLOWED — June Total Revenue Anomaly

June Revenue is intentionally elevated relative to surrounding months.

Depending on the anomaly-detection configuration, the system may also identify total June Revenue as an anomaly.

This finding is:

`ALLOWED`

It is not required for MVP success.

It must not be treated as a false positive if supported by the configured statistical method.

---

# 21. ALLOWED — Online vs Store Contrast

Controlled May-to-June channel values:

May:

* Online: 550K
* Store: 450K

June:

* Online: 780K
* Store: 520K

Expected approximate changes:

Online:

`+41.82%`

Store:

`+15.56%`

The system may detect that Online substantially outpaced Store.

This is a valid secondary Contrast finding.

It is not required as a primary Golden Truth insight.

---

# 22. ALLOWED — Karadeniz Revenue Growth

Karadeniz Revenue:

May:

`90K`

June:

`125K`

Expected change:

`≈ +38.89%`

This is a valid segment-level change.

However, its contribution to the total net Revenue increase is much smaller than Marmara's.

The system may detect this as a secondary finding.

---

# 23. FORBIDDEN — Marketing Caused Revenue Growth

The following conclusion must not be presented as fact:

> MarketingSpend caused the Revenue increase.

Reason:

The dataset provides observational co-movement only.

No controlled experiment or other causal evidence is available.

---

# 24. FORBIDDEN — Higher Prices Caused Revenue Growth

The following conclusions must not be presented as established facts:

> Prices increased.

> Higher prices caused Revenue growth.

> Pricing changes drove AverageOrderValue growth.

Reason:

The dataset does not contain:

* UnitPrice,
* PricingChange,
* explicit pricing-policy information.

AverageOrderValue is not equivalent to UnitPrice.

---

# 25. FORBIDDEN — Smart Watch Sustained Growth Trend

The system must not describe Smart Watch as having a reliable sustained upward Revenue trend based on the June spike.

Reason:

The value returns close to its historical range in July.

Expected interpretation:

Anomaly / one-off event rather than persistent growth.

---

# 26. FORBIDDEN — Bluetooth Speaker Reliable Growth Trend

The system must not report a reliable sustained growth trend for Bluetooth Speaker when the apparent movement is dominated by the September outlier.

If a trend detector initially identifies a candidate trend, Insight Integrity should qualify or reject it after outlier sensitivity is considered.

---

# 27. FORBIDDEN — Uniformly Positive Business Performance

The system must not interpret the May-to-June event as uniformly positive based only on Revenue growth.

Reason:

During the same period:

* Orders decline.
* Customers decline.

The final story should preserve this counter evidence.

---

# 28. Required Relationship Expectations

The following relationships are expected conceptually:

| Source Finding          | Target Finding       | Expected Relationship |
| ----------------------- | -------------------- | --------------------- |
| Marmara Revenue growth  | Total Revenue growth | CONTRIBUTES_TO        |
| Orders decline          | Revenue growth       | COUNTER_SIGNAL        |
| Customers decline       | Revenue growth       | COUNTER_SIGNAL        |
| MarketingSpend increase | Revenue increase     | CO_MOVES_WITH         |

No `CAUSES` relationship should be generated from these observations.

---

# 29. Expected Data Integrity Interpretation

The clean dataset should satisfy the declared analytical contract.

Important consistency expectations include:

* Revenue totals remain consistent across aggregations.
* Region-level Revenue sums to total Revenue.
* Product-level Revenue sums to total Revenue.
* Channel-level Revenue sums to total Revenue.
* Products map to their canonical Categories.
* Returns do not exceed Quantity.
* Required additive metrics remain non-negative.
* Discount remains within its defined valid range.

The dirty dataset intentionally violates selected rules and is documented separately in the Golden Truth JSON.

---

# 30. Golden Truth Testing Philosophy

Golden Truth should validate analytical behavior rather than lock the implementation to a specific algorithm.

Therefore, fixed expectations should be used for directly verifiable facts such as:

* Revenue change,
* Orders change,
* Customers change,
* Contribution share,
* deterministic derived metrics.

Behavioral expectations should be used for method-dependent outputs such as:

* anomaly classification,
* trend persistence,
* outlier dependency,
* Business Relevance ranking,
* causality status.

The Golden Truth must not prematurely require exact values for:

* Confidence Score,
* Importance Score,
* anomaly Z-score,
* Business Relevance Score,
* Relationship Strength.

These values will depend on algorithms defined during later development days.

---

# 31. Expected Final Executive Story Behavior

The exact final wording is not fixed because narration belongs to the LLM layer.

However, the final story should preserve the following meaning:

1. Revenue increased materially between May and June.
2. Marmara was the main contributor to the increase.
3. Orders and Customers declined during the same period.
4. MarketingSpend increased but its causal role is not established.
5. Relevant missing context should be disclosed.
6. Unsupported pricing or causal explanations must not be introduced.

The final story must remain grounded in validated structured findings and must later pass Story Auditor checks.
