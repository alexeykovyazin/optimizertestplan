# Review of PR 42, 44, 45 (2026-11-20)

Code: E:\Projects_Big\hqbird-impropt at origin/v5.0-impr-opt 805d25516a.
Tests: scratchpad wct/agg_nested.sql, wct/deg_desc.sql (local engine engine13_wc3.dll).

Status: A1 is fixed in PR 47 (https://github.com/IBSurgeon/hqbird/pull/47, commit 8f2c345d7f).
Nested subquery test Q1-Q9, regression suite (64 tests) and fuzz w1-w4 show no result differences.

## Confirmed by a test

| # | PR | Severity | Defect | Test result |
|---|----|----------|--------|-------------|
| A1 | 44 | High (wrong result) | An outer reference inside a nested subquery (derived table, GROUP BY, DISTINCT) is not seen by RowWeightContext::refers / FilteredStream::isDependent / HashJoin::markCounted. The stream is counted, the filter or the select list reads the last record only. Cause: collectStreams does not walk AggregateSourceNode, rse_sorted, rse_projection. | Q1 3600 vs 3544, Q2 4400 vs 4287, Q4 2900 vs 2858. With AggregateJoinCounting = false all equal. UNION and a plain correlated subquery are correct. |
| B1 | 45 (and vanilla) | Medium | DESC compound index: a segment that ends at a 4-byte chunk boundary. The walk reads the segment marker from the new key, two values are counted as one. The same code in BTR_selectivity gives a wrong RDB$INDEX_SEGMENTS.RDB$STATISTICS. | IDs 2^21..: degree 6.00 instead of 3.00, segment selectivity 100 distinct instead of 200. Small IDs and ASC index: correct. |

## Confirmed by reading the code

| # | PR | Severity | Defect |
|---|----|----------|--------|
| C1 | 42/43 | Medium | JoinOrderDP fillChain resets the prefix slots: orderedField and equiMatches are lost. isOrderedLookup() prices DP transitions differently from the replay. The replay result replaces the greedy order without a check against the greedy bestCost (JoinOrderDP.cpp:518-543). The DP can return an order more expensive than the greedy one. |
| B2 | 45 | Low-medium | getKeyDegree, multi-column: average = cardinality / nd counts NULL-prefix rows; D and nd do not (StatisticsCache.cpp:3507). The ratio is too low, the skew is hidden. |
| B3 | 45 | Low | The worst case batched hash price uses bhjSpillShare computed for E, not W (InnerJoin.cpp:556-559). |
| B4 | 45 | Design | D is exact over the index; avg comes from sampled ndistinct. In SAMPLE mode a uniform key can get r > 1. |
| B5 | 45 | Low | getWorstRatio uses MIN(lowerCount, upperCount): a last range / STARTING segment counts as an equality prefix. |
| C2 | 42 | Low-medium | The clustering test samples one middle leaf: a leaf of one dominant key or NULLs gives a small ratio, the table is taken as clustered. |
| C3 | 42 | Low-medium | The cache size is bcb_count (run-time). It grows by num_buffers DPB / gfix -buffers; Classic/SuperClassic have 256 pages. Plans depend on server mode and on the client. |
| C4 | 42 | Low | LEFT JOIN loop/hash choice and the navigation choice do not add the page miss cost. |
| A2 | 44 | Low | Weighted SUM checks v*w for overflow before adding: a mixed-sign sum can fail where the plain path does not. |
| A3 | 44 | Low-medium | The collapsed hash build trusts the index selectivity, has no run-time cap on distinct keys. |
| A4 | 44 | Low | The weight overflow error is raised when only MIN/MAX/DISTINCT aggregates are present. |

## Improvement suggestions

1. PR 44: one stream collector that walks nested RSEs, maps, sort and projection lists (fixes A1 and the same gap in FilteredStream / HashJoin).
2. PR 44: price the counting in the join order (the plan is chosen as if all rows go up to the aggregate).
3. PR 45: count the runs and non-NULL entries per prefix in the same walk; store avg with D (fixes B2, B4).
4. PR 45: one shared segment-compare helper for BTR_selectivity and BTR_key_degrees (fixes B1 in both).
5. PR 45: cache worstRatio per candidate; support inversions with more than one index (FK + filter index).
6. PR 42/43: keep orderedField and the hash-in-prefix bit in DPState; accept the replay only if it is cheaper than the greedy order.
7. PR 42: a stable cache size (configured or header page buffers), lower price for sequential misses.
