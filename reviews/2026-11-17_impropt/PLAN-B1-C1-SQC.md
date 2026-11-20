# Fix plan: SQC (wrong result), B1, C1 (2026-11-20)

Code: E:\Projects_Big\hqbird-impropt, base origin/v5.0-impr-opt 805d25516a plus PR 47
(https://github.com/IBSurgeon/hqbird/pull/47, the deep stream collector `collectAllStreams`).
Review: REVIEW-PR42-45.md in this folder.

Order: SQC first (wrong result), then B1 (wrong statistics), then C1 (plan cost).
Each fix is one branch from origin/v5.0-impr-opt and one PR.

## 1. SQC: EXISTS/IN to semi-join conversion gives a wrong result

### Facts (tested today)

- Setting: `SubQueryConversion = true` (default false). The code is vanilla Firebird 5:
  `findPossibleJoins()`, RecordSourceNodes.cpp:143-242.
- Cause: the check "no outer references left in the subquery" uses `rse->collectStreams()`
  (line 203). It does not walk a nested derived table, aggregate, UNION, DISTINCT/ORDER BY.
  The subquery becomes a semi-join while it still refers to the outer stream.
  The hash table is built once, with the outer record of the build moment.
- Test wct/semi_nested.sql, database of wct/agg_nested.sql:

| Query | Outer reference inside | ON | OFF (correct) |
|-------|------------------------|----|---------------|
| S1 | derived table | 2858 | 972 |
| S2 | DISTINCT derived table (IN) | 2858 | 972 |
| S3 | UNION derived table | 2144 | 1444 |
| S4 | GROUP BY + ROWS | 714 | 2513 |

- The base engine (HQbird 5.0.5 without the optimizer work) gives the same wrong values.
  So it is an upstream bug, not a PR 42-45 bug.

### Fix

1. Branch `v5.0-impr-opt-sqc-nested` from origin/v5.0-impr-opt after PR 47 is merged
   (it needs `collectAllStreams`).
2. In `findPossibleJoins()` replace `rse->collectStreams(streams)` with `collectAllStreams(rse, streams)`.
   Move the forward declaration of `collectAllStreams` above the anonymous namespace.
3. In `findDependentBooleans()`: a conjunct that refers to an outer stream only through a nested
   subquery must not become a join key. If `hidesStreams(conjunct, rseStreams)` is true,
   leave the conjunct in the subquery (then the subquery stays dependent and is not converted).
4. Check the other `collectStreams` users in the conversion path (line 3683 and the
   anti-join path for NOT EXISTS / NOT IN) and apply the same rule.
5. Docs: README.optimizer-improvement EN/RU, a short note in the SubQueryConversion part.

### Tests

- S1-S4 plus the NOT EXISTS / NOT IN forms, ON vs OFF: equal counts.
- Plain correlated EXISTS / IN (no nested subquery): still converted, the plan still shows HASH.
- Regression suite (64 tests) with SubQueryConversion = true and false; fuzz w1-w4.
- Later (outward-facing, only with the user's approval): report it to FirebirdSQL/firebird
  with S1 as the repro. First check if master already has a fix.

## 2. B1: DESC compound index, a segment that ends at a 4-byte boundary

### Facts

- `BTR_selectivity()` (btr.cpp:3094-3167) and `BTR_key_degrees()` (btr.cpp:3350+, PR 45)
  use the same segment-compare code.
- When the node prefix ends exactly on a segment marker (`i == pos`), the code takes the
  marker from the new key: `count = *p2`. The markers differ there: one key continues
  segment s, the other key starts segment s+1. In an ASC index the new key is the one that
  continues s, so the result is correct. In a DESC index the bytes are complemented and the
  new key is the one that starts s+1. Two different values of segment s count as one.
- Test wct/deg_desc.sql: DESC (id, x), ids from 2^21: degree 6.00 instead of 3.00,
  segment selectivity 100 distinct instead of 200. Vanilla RDB$STATISTICS is wrong too.

### Fix

1. Branch `v5.0-impr-opt-desc-keys`.
2. One static helper for both functions:
   `static ULONG firstDifferentSegment(const temporary_key& prev, const IndexNode& node, bool descending)`.
   At `i == pos` take the marker of the previous chunk (`p1 + i - (STUFF_COUNT + 1)`):
   it is the segment that both keys share up to this point. Un-complement it for DESC.
3. Replace the two copies of the loop with the helper.

### Tests

- Matrix: ASC/DESC x 2 and 3 segments x small ids / ids from 2^21 (boundary) x
  string segments of length 3, 4, 5, 8 x trailing NULL / empty segment.
  Expected values from SQL: `count(distinct ...)` per prefix and the exact degree query.
- RDB$INDEX_SEGMENTS.RDB$STATISTICS after SET STATISTICS: equal to 1 / distinct.
- Regression suite: plan changes are expected only for DESC compound indexes; check each one.
- Upstream note as for SQC (vanilla `BTR_selectivity`).

## 3. C1: JoinOrderDP prices the transitions with empty prefix slots

### Facts

- `fillChain()` (JoinOrderDP.cpp:294-310) calls `joinedStreams[position].reset()` for every
  prefix position. `reset()` clears `orderedField` and `equiMatches` (Optimizer.h:1365-1372).
- `isOrderedLookup()` (InnerJoin.cpp:847) reads both: `equiMatches.hasData()` (a hash in the
  prefix breaks the order) and `orderedField` (the driver comes in key order).
  So a DP transition sees "no hash, no order"; the replay sees the real values.
  The DP state cost and the replay cost of the same chain can differ.
- The replay result replaces the greedy order without a cost check
  (JoinOrderDP.cpp:518-543: `bestCost = totalCost`). The DP can return an order that is
  more expensive than the greedy one. (`completePartialOrder` already has this check.)

### Fix

1. Branch `v5.0-impr-opt-dp-slots`.
2. DPState: add `SSHORT orderedField` (of the last position) and `FB_UINT64 hashBits`
   (bit k: position k joined by hash). Fill them after `estimateCost()` of a transition.
3. `fillChain()`: restore `orderedField` and the hash bit of each prefix slot.
   Add a `hashJoined` flag to the slot, set together with `equiMatches`;
   `isOrderedLookup()` reads the flag instead of `equiMatches.hasData()`.
4. Replay guard: keep a copy of the greedy `bestStreams` / `bestCost`.
   Accept the replay only if `totalCost < greedyCost`; else restore the copy.
5. Debug check (debug build only): `fb_assert` that the replay cost equals the DP state cost
   within 1e-6 relative.

### Tests

- A counter in a debug build: number of DP winners where replay cost != state cost,
  and where replay cost > greedy cost. Run the regression suite and job-light;
  before the fix > 0 expected, after the fix 0.
- A synthetic query: 5-6 tables, a chain of ordered lookups (PR 42 locality) and one hash
  position, where the DP picks a different order than the greedy search.
- Regression suite, fuzz w1-w4 (results), job-light time on dellg15 (no profiler).

## Effort

| Fix | Code | Tests | Risk |
|-----|------|-------|------|
| SQC | small (2 functions) | 1 day | low: less conversion in rare cases |
| B1 | small (1 helper) | 1 day | medium: statistics change for DESC compound indexes |
| C1 | medium (DPState, slot flag, guard) | 1-2 days | medium: DP plans can change |
