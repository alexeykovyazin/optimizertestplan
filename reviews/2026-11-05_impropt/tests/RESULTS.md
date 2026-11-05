# Tests on 87a3e409cd (local build 05.11, embedded, ExtendedStatistics=true via databases.conf)

Fixed (test):
- S1: count(*) having / max() subquery filter / count+sum filter: OK
- S2: range on column added after REFRESH: no crash
- S3: create table tb(bins int): OK
- S4: REFRESH SAMPLE: CARD_EXACT=false, fraction 0.309, card 100004 (true 100000)
- S5: STAT$SCALE=-2; n = 12.34 -> 963 (true 1000)
- S7: ALTER COLUMN TYPE int->bigint, int->varchar + REFRESH: no crash, a=7 -> 400 (true 400)

Still present (test):
- S11: NONE db, 'caf\xe9' -> REFRESH fails "Malformed string", whole run rolled back
- M1: LEFT JOIN 20k x 20k without indexes -> Nested Loop (outer) + full scan of OB per row,
  even with exact stats (estimates 20000/1.00 correct). Timeout >200 s.
  Inner JOIN -> Hash Join.
- M2: CONFIRMED WRONG RESULTS (17_m2.sql, 18_m2def.sql). With index ob_x on ob(x):
  Hash Join (outer) chosen; `oa left join ob on oa.x = ob.x and ob.y > oa.z` -> count(ob.x) 20000,
  correct 9000 (NL plan with oa.x+0 gives 9000). OR residual `(ob.y > oa.z or ob.y = 0)` -> 20000, correct 10000.
  Same on DEFAULT config (no alias, ExtendedStatistics off). Local-only ON filter ob.y > 10 is correct (9000).
- M1 root cause (agent C): OuterJoin.cpp:251 matchSelectivity = loop retrieval selectivity, 1.0 without index
  on inner key (outer field not computable) -> hashCost 8.8e8 > loopCost 4e8.
- E8: UTF8 text: s >= 'v5' -> 28307 (true 11000); s < 'v5' -> 88647 (true 89000); sum 117%;
  between 'v2' and 'v3' -> 44465 (true 22400)

New (test):
- R1 unique column (no MCV): collector keeps 1-bin histogram [min,max] (Collector.cpp:1541),
  estimator adds whole bin for open upper end (StatisticsCache.cpp:627-628) ->
  x >= 50000 / x > 49999 / x >= 99000 -> 100000 (=100%, true 50%/50%/1%).
  x between 50000 and 50999 -> 51025 (true 1000).
- R2 SAMPLE ND capped by sample rows: Collector.cpp:1502-1503 MIN(..., MAX(nonNull, d)), nonNull = sample.
  unique 100k column -> ND 30000 (Shlosser gives 100000). Before S4 fix this path was dead.
- R3 unclamped selectivity on column with stats when distribution path fails
  (parameter, expression, NONE charset text): Optimizer.cpp:2132 MAX(sel*(1-null), min) without MIN(.,1);
  sel = factor 0.05 * adjustment 100 = 5.0.
  y > ? -> 500000 (5x table 100k); y between ? and ? -> 2,500,000 (25x); y > 1 + 1 -> 500000;
  NONE text sn >= 'v5' -> 500000; tz.y > oa.x join NL rows=1e9.
- R4 BETWEEN decomposed into >= AND <= (Optimizer.cpp:2600) and multiplied as independent:
  y between 10000 and 10199 -> 26028 (true 1000, x26); same for y >= 10000 and y <= 10199.
  The new blr_between branch at Optimizer.cpp:1688 is dead code.
- N1 (agent A, test 20_n1.sql): store without STAT$SCALE (created before 867eb9ed0f), ExtendedStatistics=true ->
  `select count(*) from q where x = 1` fails "Column unknown STAT$SCALE"; REFRESH fails too. Only DROP+ADD helps.
- S8 test 19_s8.sql: not reproduced (optimizer chose plain HJ + Sort, hashed side 100k). Stays [код].
- R5 no stats: inner join 20k x 20k 1:1 -> 432,374 rows; LEFT JOIN same keys -> 43,237,411 (x100 vs inner).
