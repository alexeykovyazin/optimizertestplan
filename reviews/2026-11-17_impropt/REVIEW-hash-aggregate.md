# Review of the hash aggregation and the hash unique (2026-11-22, draft)

Code: `origin/v5.0-impr-opt` at `8d6c1d0568`. Commits: `6c7c834cd6` (Hash Aggregate), `e22f591368`,
`9fb180d41b` (Hash Unique), `8d6c1d0568` (the spill of both, the choice by estimated counts).
Build: engine `hu1` of that commit (md5 `ea3f5ebc2e38`). Parameter: `AggregateHashMemory` (8M by default, 0 = off).

Method: two independent code readings (the execution, the choice of the plan), then every finding was run
on the build. The reference is the same query with `AggregateHashMemory = 0` (the sorted path).
Tests: `tests/71_hash_agg_defects.sql` (default configuration), `tests/72_hash_agg_spill.sql`
(`AggregateHashMemory = 512K`). Outputs: `tests/out_hash_71_*`, `tests/out_sorted_71_*`, `tests/out_hash_72_*`,
`tests/out_sorted_72_*`.

Status: nothing is fixed. With the default configuration the build gives wrong results and crashes.
Recommendation: set `AggregateHashMemory = 0` until A1-A5 are fixed.

## Confirmed by a test: wrong results, crashes, memory

| # | Severity | Defect | Test result |
|---|----------|--------|-------------|
| A1 | High: wrong result, crash. Default configuration | `HashPartitionReader::next` (HashPartition.h) mixes two read paths. A record that crosses a block boundary of the temp space is read through the chunk buffer; the next records come from `peekMemory` and do not move `m_chunkOffset`. At the next boundary the chunk is not read again and the address `m_chunk + (m_position - m_chunkBase) * length` is far past the buffer. It needs a partition larger than 2 MB and a record length that does not divide the block size (1 MB): 48 bytes here. | `select id, count(*) from t where id < N group by id`, no index on `id`: N = 80 000 correct; N = 150 000: the sum of the counts is 115 413 007, not 150 000; N = 300 000: 299 993 groups; N = 1 000 000: the process crashes. Hash Unique uses the same reader. |
| A2 | High: wrong result, use after free. Default configuration | MIN/MAX of a text. The saved state of a group is a `memcpy` of `impure_value_ex`; the text lives in the heap string `vlu_string`, so all the groups share one buffer. A longer value frees the buffer the other groups point to. | `select d, max(n), min(n) from e group by d`: `1 yy azz / 2 y a` instead of `1 zzz yy / 2 a a`. The battery: 5 of 44 queries differ (all with MIN/MAX of a text), the default budget crashes on `group by txt` with 100 000 groups. |
| A3 | High: wrong result. Default configuration | Hash Unique compares the raw record image. The sort compares the keys after `Sort::diddleKey`: trailing spaces of a VARCHAR, -0 and +0, the DECFLOAT form, the time zone bytes. | `select distinct` over two equal values gives 2 rows instead of 1 for: `'a'` / `'a '`, `0e0` / `-0e0`, `1.0` / `1.00` (DECFLOAT), one instant in two time zones. Hash Aggregate is correct here. |
| A4 | High: wrong result. Spill | `composePartitionRow` (HashAggregateStream.cpp:848-858) takes the dbkey, the transaction number and the valid flag of stream k from `m_partFields[k].stream`: the stream of field k, not stream k. Fewer fields than streams: a read past the array. | `count(b.rdb$db_key)` over `a left join b` with a spill (512K): 17 720 instead of 10 000. |
| A5 | High: crash. Spill past the temp cache | `HashPartitionWriter::append` flushes only when `m_pendingCount == 16384`. A record length that does not divide 16384 never gives the equality; `memcpy` writes past the 16384-byte buffer. The buffered mode starts when the temp space leaves memory (the temp cache is full). | `TempCacheLimit = 0`: the first spilling GROUP BY and the first spilling DISTINCT (record length 28) crash the process (access violation in firebird.log). |
| A6 | Medium: memory leak | `GroupHashTable` has no destructor: the slot blocks stay in the request pool. Every open and every partition pass leaks them. | A correlated sub-query with GROUP BY over 20 000 outer rows: Max memory 1 332 MB; the sorted path 58 MB. |
| A7 | Medium: memory | The bucket array of Hash Unique is sized by `hashEstimatedGroups`: the product of the index distinct counts with no cap (the cardinality is 0 at that time). Up to 2^31 buckets (8 GB) per open. | `select distinct a, b, c` over 100 000 rows, three indexed columns of 1000 values: about 1 GB allocated, 0.37 s against 0.08 s. |
| A8 | Low: endless loop | A budget smaller than one group slot: the gate has `groupsFit < 1` in double and takes the spill; the executor has `m_groupsFit = 0`, every row spills again into the single partition. | `AggregateHashMemory = 100`, `select a, count(*) from p1 where a = 1 group by a`: no end after 60 s. |

## Confirmed by a test: the choice of the plan

| # | Severity | Defect | Test result |
|---|----------|--------|-------------|
| B1 | High: regression | The gate does not look at the first-rows mode. FIRST / ROWS / EXISTS over GROUP BY read the whole input; before, the index navigation stopped after the first groups. | `select first 1 a, count(*) from t group by a` (1 000 000 rows): 1 031 261 fetches against 27 832. The same for EXISTS and with ORDER BY. |
| B2 | Medium: error on a working query | A user `PLAN (T ORDER T_A)` for a GROUP BY: the hash is taken, the navigation is not built, `checkIndices` raises the error. | "index T_A cannot be used in the specified plan". The sorted path: no error. |
| B3 | Medium: regression | `decideHashUnique` returns true for every plain DISTINCT; `checkSorts` then keeps the ORDER BY. When `generateSort` goes back to the sort, the plan has two sorts. | `select distinct id, b from t order by id, b`: Sort over Unique Sort. Before: one Unique Sort. |
| B4 | Medium: bad plan | Without the extended statistics the gate takes 1000 rows as the input (`csb_cardinality` is 0 at that time). A nearly unique grouping of any size takes the hash with one partition (`rows=1000.00` in the plan). The spill then removes only `groupsFit` groups per pass. | The plan of `select id, count(*) from t group by id` over 1 000 000 rows is Hash Aggregate. The run time could not be compared: A1 breaks this query. |
| B5 | Low | The legacy plan `PLAN HASH UNIQUE (U NATURAL)` is not valid PLAN syntax. | The plan text given back raises "Token unknown - unique". |

## Found by the code reading, not run

| # | Severity | Defect |
|---|----------|--------|
| C1 | Medium: resource leak | The partition writers are never deleted; `close()` does not free `impure->partitions`. On an early close (FIRST n, EXISTS) or an error, `~TempSpace` never runs: the temp cache usage of the database is not given back, the temp files stay open. The sorts avoid this through `req_sorts`. |
| C2 | Medium: performance | The partition number and the bucket number use the same low hash bits: inside a partition only 1 / 2^shift of the buckets are used. With shift 0 there is no real re-partitioning. `hash >> shift` with shift >= 32 is undefined (fan-out 64, level 5). |
| C3 | Low | The exact-count test accepts a partial index and skips non-field grouping items (`group by a, b + 0` is counted as distinct(a)). |
| C4 | Low | The optimizer notes have two sections 4.36 and two sections 4.37. |

Reported by the reading and not reproduced: a group key of `COALESCE(int, numeric)` copied with the compile-time
length (the test gave the correct `1.00 3`).

## Checked and found correct

- After a hash hit the full key is compared. NULL and zero are different groups in Hash Aggregate.
- Hash Aggregate keys: CI/AI collations, the padding of a text, DECFLOAT, -0 / +0, the time zone types.
- A group is never split between the resident table and a partition.
- `AggregateHashMemory = 0` turns both methods off on every path.
- ORDER BY over a hash GROUP BY is kept in every form. Window functions and merge joins sort themselves.
- The row weights of the counting aggregate (4.32) never meet the hash: they need no GROUP BY.
- COUNT, SUM, AVG, STDDEV / VAR, CORR keep their state inside the impure area: the `memcpy` save is correct.

## The local battery

`SP/hu/bat_q.sql`: 44 GROUP BY / DISTINCT queries over 200 000 rows (integer, text with a CI collation, padded
text, DECFLOAT, DOUBLE, time zone, BOOLEAN, INT128 and DATE keys; joins, outer joins, sub-queries, HAVING,
FILTER, window, UNION, early close in PSQL). The sorted path is the reference.

| AggregateHashMemory | Hash Aggregate plans | Hash Unique plans | Result |
|---------------------|----------------------|-------------------|--------|
| 0 | 0 | 0 | the reference |
| 16K | 5 | 0 | equal |
| 512K | 19 | 0 | 4 queries differ (A2), the process crashes at query 45 (a spill of 200 000 groups; A1 is the likely cause) |
| 8M (default) | 21 | 4 | 4 queries differ (A2), the process crashes at query 31 (a spill with MIN/MAX of a text; A1 or A2) |
| 512M | 21 | 9 | 5 queries differ (A2) |

## Stand

Draft: the timing is not done yet.

- Plans of the 691 stand queries (job-light, scale, CEB), the hash on and off: job-light and scale have no
  GROUP BY, their plans are the same. All the 90 CEB queries with GROUP BY take Hash Aggregate with the hash on;
  with the hash off the plans are the same as before these commits.
- Timing sets: TPC-H, JCC-H (norm, skew) and DSB (s1, s2) of this repository, scale factor 1. The databases
  are on the stand; the extended statistics and the plans are being collected.

## Suggested fixes

1. A1: one read path per reader, or test the chunk by the position range: `m_position < m_chunkBase ||
   m_position >= m_chunkBase + m_chunkCount`.
2. A2: keep the text state inside the slot (a fixed area of the declared length), or do not take the hash when a
   MIN/MAX argument is a text / dbkey.
3. A3: build the hash key of Hash Unique from the normalized sort key (run the `diddleKey` step), as Hash
   Aggregate does.
4. A4: `request->req_rpb[partStream.stream]`.
5. A5: flush when `m_pendingCount + m_recordLength > BUFFER_SIZE`.
6. A6, C1: a destructor for `GroupHashTable`; register the table, the writers and the partitions with the request
   (as `req_sorts` does) and free them in `close()`.
7. A7, B4: pass the capped estimate; take the cardinality as `compileRelation` does; at least 2 partitions once
   the spill starts; `m_groupsFit = MAX(1, ...)` and no hash when `groupsFit < 1` (A8).
8. B1, B2: no hash in the first-rows mode and under a user PLAN, or price the navigation as the retrieval does.
9. B3: decide the method before `checkSorts`, or keep the outer sort only when the final choice is the hash.
10. B5: print `SORT (` in the legacy plan, as the sorted path does.
