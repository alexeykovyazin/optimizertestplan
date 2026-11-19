SET LIST ON;
SET STATS ON;

WITH RECURSIVE s AS (
  SELECT 0 AS N FROM RDB$DATABASE
  UNION ALL
  SELECT s.N + 1 FROM s WHERE s.N < 63
),
par AS (SELECT 0e0 AS A, 1024e0 AS M FROM RDB$DATABASE),
tot AS (
  SELECT
    SUM(IIF(x.C_CI > 0, POWER(x.C_CI, p.A), 0e0)) / MAX(p.M) AS T_CI,
    SUM(IIF(x.C_MK > 0, POWER(x.C_MK, p.A), 0e0)) / MAX(p.M) AS T_MK,
    SUM(IIF(x.C_MI > 0, POWER(x.C_MI, p.A), 0e0)) / MAX(p.M) AS T_MI,
    SUM(IIF(x.C_MC > 0, POWER(x.C_MC, p.A), 0e0)) / MAX(p.M) AS T_MC
  FROM X3_KEY x CROSS JOIN par p
),
k AS (
  SELECT x.U,
    CAST(x.C_CI AS DOUBLE PRECISION) * x.C_MK * x.C_MI * x.C_MC AS X,
    MINVALUE(1e0,
      POWER(x.C_CI, p.A) / t.T_CI, POWER(x.C_MK, p.A) / t.T_MK,
      POWER(x.C_MI, p.A) / t.T_MI, POWER(x.C_MC, p.A) / t.T_MC) AS PI
  FROM X3_KEY x CROSS JOIN tot t CROSS JOIN par p
  WHERE x.C_CI > 0 AND x.C_MK > 0 AND x.C_MI > 0 AND x.C_MC > 0
),
e AS (
  SELECT s.N, SUM(k.X / k.PI) AS EST, COUNT(*) AS MATCHED
  FROM k CROSS JOIN s
  WHERE (k.U + s.N / 64e0) - FLOOR(k.U + s.N / 64e0) < k.PI
  GROUP BY s.N
),
j AS (SELECT SUM(X) AS J FROM k)
SELECT '0/1024' AS E3_A_M,
  COUNT(*) AS SAMPLES,
  AVG(e.EST / j.J) AS R_AVG,
  MIN(e.EST / j.J) AS R_MIN,
  MAX(e.EST / j.J) AS R_MAX,
  SUM(IIF(e.EST BETWEEN j.J / 2 AND j.J * 2, 1, 0)) AS IN_X2,
  SUM(IIF(e.EST BETWEEN j.J / 10 AND j.J * 10, 1, 0)) AS IN_X10,
  SUM(IIF(e.EST > j.J * 2, 1, 0)) AS OVER_X2,
  SUM(IIF(e.EST < j.J / 2, 1, 0)) AS UNDER_X2,
  MIN(e.MATCHED) AS MATCHED_MIN,
  MAX(e.MATCHED) AS MATCHED_MAX
FROM e CROSS JOIN j;

WITH RECURSIVE s AS (
  SELECT 0 AS N FROM RDB$DATABASE
  UNION ALL
  SELECT s.N + 1 FROM s WHERE s.N < 63
),
par AS (SELECT 0e0 AS A, 4096e0 AS M FROM RDB$DATABASE),
tot AS (
  SELECT
    SUM(IIF(x.C_CI > 0, POWER(x.C_CI, p.A), 0e0)) / MAX(p.M) AS T_CI,
    SUM(IIF(x.C_MK > 0, POWER(x.C_MK, p.A), 0e0)) / MAX(p.M) AS T_MK,
    SUM(IIF(x.C_MI > 0, POWER(x.C_MI, p.A), 0e0)) / MAX(p.M) AS T_MI,
    SUM(IIF(x.C_MC > 0, POWER(x.C_MC, p.A), 0e0)) / MAX(p.M) AS T_MC
  FROM X3_KEY x CROSS JOIN par p
),
k AS (
  SELECT x.U,
    CAST(x.C_CI AS DOUBLE PRECISION) * x.C_MK * x.C_MI * x.C_MC AS X,
    MINVALUE(1e0,
      POWER(x.C_CI, p.A) / t.T_CI, POWER(x.C_MK, p.A) / t.T_MK,
      POWER(x.C_MI, p.A) / t.T_MI, POWER(x.C_MC, p.A) / t.T_MC) AS PI
  FROM X3_KEY x CROSS JOIN tot t CROSS JOIN par p
  WHERE x.C_CI > 0 AND x.C_MK > 0 AND x.C_MI > 0 AND x.C_MC > 0
),
e AS (
  SELECT s.N, SUM(k.X / k.PI) AS EST, COUNT(*) AS MATCHED
  FROM k CROSS JOIN s
  WHERE (k.U + s.N / 64e0) - FLOOR(k.U + s.N / 64e0) < k.PI
  GROUP BY s.N
),
j AS (SELECT SUM(X) AS J FROM k)
SELECT '0/4096' AS E3_A_M,
  COUNT(*) AS SAMPLES,
  AVG(e.EST / j.J) AS R_AVG,
  MIN(e.EST / j.J) AS R_MIN,
  MAX(e.EST / j.J) AS R_MAX,
  SUM(IIF(e.EST BETWEEN j.J / 2 AND j.J * 2, 1, 0)) AS IN_X2,
  SUM(IIF(e.EST BETWEEN j.J / 10 AND j.J * 10, 1, 0)) AS IN_X10,
  SUM(IIF(e.EST > j.J * 2, 1, 0)) AS OVER_X2,
  SUM(IIF(e.EST < j.J / 2, 1, 0)) AS UNDER_X2,
  MIN(e.MATCHED) AS MATCHED_MIN,
  MAX(e.MATCHED) AS MATCHED_MAX
FROM e CROSS JOIN j;

WITH RECURSIVE s AS (
  SELECT 0 AS N FROM RDB$DATABASE
  UNION ALL
  SELECT s.N + 1 FROM s WHERE s.N < 63
),
par AS (SELECT 1e0 AS A, 1024e0 AS M FROM RDB$DATABASE),
tot AS (
  SELECT
    SUM(IIF(x.C_CI > 0, POWER(x.C_CI, p.A), 0e0)) / MAX(p.M) AS T_CI,
    SUM(IIF(x.C_MK > 0, POWER(x.C_MK, p.A), 0e0)) / MAX(p.M) AS T_MK,
    SUM(IIF(x.C_MI > 0, POWER(x.C_MI, p.A), 0e0)) / MAX(p.M) AS T_MI,
    SUM(IIF(x.C_MC > 0, POWER(x.C_MC, p.A), 0e0)) / MAX(p.M) AS T_MC
  FROM X3_KEY x CROSS JOIN par p
),
k AS (
  SELECT x.U,
    CAST(x.C_CI AS DOUBLE PRECISION) * x.C_MK * x.C_MI * x.C_MC AS X,
    MINVALUE(1e0,
      POWER(x.C_CI, p.A) / t.T_CI, POWER(x.C_MK, p.A) / t.T_MK,
      POWER(x.C_MI, p.A) / t.T_MI, POWER(x.C_MC, p.A) / t.T_MC) AS PI
  FROM X3_KEY x CROSS JOIN tot t CROSS JOIN par p
  WHERE x.C_CI > 0 AND x.C_MK > 0 AND x.C_MI > 0 AND x.C_MC > 0
),
e AS (
  SELECT s.N, SUM(k.X / k.PI) AS EST, COUNT(*) AS MATCHED
  FROM k CROSS JOIN s
  WHERE (k.U + s.N / 64e0) - FLOOR(k.U + s.N / 64e0) < k.PI
  GROUP BY s.N
),
j AS (SELECT SUM(X) AS J FROM k)
SELECT '1/1024' AS E3_A_M,
  COUNT(*) AS SAMPLES,
  AVG(e.EST / j.J) AS R_AVG,
  MIN(e.EST / j.J) AS R_MIN,
  MAX(e.EST / j.J) AS R_MAX,
  SUM(IIF(e.EST BETWEEN j.J / 2 AND j.J * 2, 1, 0)) AS IN_X2,
  SUM(IIF(e.EST BETWEEN j.J / 10 AND j.J * 10, 1, 0)) AS IN_X10,
  SUM(IIF(e.EST > j.J * 2, 1, 0)) AS OVER_X2,
  SUM(IIF(e.EST < j.J / 2, 1, 0)) AS UNDER_X2,
  MIN(e.MATCHED) AS MATCHED_MIN,
  MAX(e.MATCHED) AS MATCHED_MAX
FROM e CROSS JOIN j;

WITH RECURSIVE s AS (
  SELECT 0 AS N FROM RDB$DATABASE
  UNION ALL
  SELECT s.N + 1 FROM s WHERE s.N < 63
),
par AS (SELECT 1e0 AS A, 4096e0 AS M FROM RDB$DATABASE),
tot AS (
  SELECT
    SUM(IIF(x.C_CI > 0, POWER(x.C_CI, p.A), 0e0)) / MAX(p.M) AS T_CI,
    SUM(IIF(x.C_MK > 0, POWER(x.C_MK, p.A), 0e0)) / MAX(p.M) AS T_MK,
    SUM(IIF(x.C_MI > 0, POWER(x.C_MI, p.A), 0e0)) / MAX(p.M) AS T_MI,
    SUM(IIF(x.C_MC > 0, POWER(x.C_MC, p.A), 0e0)) / MAX(p.M) AS T_MC
  FROM X3_KEY x CROSS JOIN par p
),
k AS (
  SELECT x.U,
    CAST(x.C_CI AS DOUBLE PRECISION) * x.C_MK * x.C_MI * x.C_MC AS X,
    MINVALUE(1e0,
      POWER(x.C_CI, p.A) / t.T_CI, POWER(x.C_MK, p.A) / t.T_MK,
      POWER(x.C_MI, p.A) / t.T_MI, POWER(x.C_MC, p.A) / t.T_MC) AS PI
  FROM X3_KEY x CROSS JOIN tot t CROSS JOIN par p
  WHERE x.C_CI > 0 AND x.C_MK > 0 AND x.C_MI > 0 AND x.C_MC > 0
),
e AS (
  SELECT s.N, SUM(k.X / k.PI) AS EST, COUNT(*) AS MATCHED
  FROM k CROSS JOIN s
  WHERE (k.U + s.N / 64e0) - FLOOR(k.U + s.N / 64e0) < k.PI
  GROUP BY s.N
),
j AS (SELECT SUM(X) AS J FROM k)
SELECT '1/4096' AS E3_A_M,
  COUNT(*) AS SAMPLES,
  AVG(e.EST / j.J) AS R_AVG,
  MIN(e.EST / j.J) AS R_MIN,
  MAX(e.EST / j.J) AS R_MAX,
  SUM(IIF(e.EST BETWEEN j.J / 2 AND j.J * 2, 1, 0)) AS IN_X2,
  SUM(IIF(e.EST BETWEEN j.J / 10 AND j.J * 10, 1, 0)) AS IN_X10,
  SUM(IIF(e.EST > j.J * 2, 1, 0)) AS OVER_X2,
  SUM(IIF(e.EST < j.J / 2, 1, 0)) AS UNDER_X2,
  MIN(e.MATCHED) AS MATCHED_MIN,
  MAX(e.MATCHED) AS MATCHED_MAX
FROM e CROSS JOIN j;

WITH RECURSIVE s AS (
  SELECT 0 AS N FROM RDB$DATABASE
  UNION ALL
  SELECT s.N + 1 FROM s WHERE s.N < 63
),
par AS (SELECT 1.5e0 AS A, 1024e0 AS M FROM RDB$DATABASE),
tot AS (
  SELECT
    SUM(IIF(x.C_CI > 0, POWER(x.C_CI, p.A), 0e0)) / MAX(p.M) AS T_CI,
    SUM(IIF(x.C_MK > 0, POWER(x.C_MK, p.A), 0e0)) / MAX(p.M) AS T_MK,
    SUM(IIF(x.C_MI > 0, POWER(x.C_MI, p.A), 0e0)) / MAX(p.M) AS T_MI,
    SUM(IIF(x.C_MC > 0, POWER(x.C_MC, p.A), 0e0)) / MAX(p.M) AS T_MC
  FROM X3_KEY x CROSS JOIN par p
),
k AS (
  SELECT x.U,
    CAST(x.C_CI AS DOUBLE PRECISION) * x.C_MK * x.C_MI * x.C_MC AS X,
    MINVALUE(1e0,
      POWER(x.C_CI, p.A) / t.T_CI, POWER(x.C_MK, p.A) / t.T_MK,
      POWER(x.C_MI, p.A) / t.T_MI, POWER(x.C_MC, p.A) / t.T_MC) AS PI
  FROM X3_KEY x CROSS JOIN tot t CROSS JOIN par p
  WHERE x.C_CI > 0 AND x.C_MK > 0 AND x.C_MI > 0 AND x.C_MC > 0
),
e AS (
  SELECT s.N, SUM(k.X / k.PI) AS EST, COUNT(*) AS MATCHED
  FROM k CROSS JOIN s
  WHERE (k.U + s.N / 64e0) - FLOOR(k.U + s.N / 64e0) < k.PI
  GROUP BY s.N
),
j AS (SELECT SUM(X) AS J FROM k)
SELECT '1.5/1024' AS E3_A_M,
  COUNT(*) AS SAMPLES,
  AVG(e.EST / j.J) AS R_AVG,
  MIN(e.EST / j.J) AS R_MIN,
  MAX(e.EST / j.J) AS R_MAX,
  SUM(IIF(e.EST BETWEEN j.J / 2 AND j.J * 2, 1, 0)) AS IN_X2,
  SUM(IIF(e.EST BETWEEN j.J / 10 AND j.J * 10, 1, 0)) AS IN_X10,
  SUM(IIF(e.EST > j.J * 2, 1, 0)) AS OVER_X2,
  SUM(IIF(e.EST < j.J / 2, 1, 0)) AS UNDER_X2,
  MIN(e.MATCHED) AS MATCHED_MIN,
  MAX(e.MATCHED) AS MATCHED_MAX
FROM e CROSS JOIN j;

WITH RECURSIVE s AS (
  SELECT 0 AS N FROM RDB$DATABASE
  UNION ALL
  SELECT s.N + 1 FROM s WHERE s.N < 63
),
par AS (SELECT 1.5e0 AS A, 4096e0 AS M FROM RDB$DATABASE),
tot AS (
  SELECT
    SUM(IIF(x.C_CI > 0, POWER(x.C_CI, p.A), 0e0)) / MAX(p.M) AS T_CI,
    SUM(IIF(x.C_MK > 0, POWER(x.C_MK, p.A), 0e0)) / MAX(p.M) AS T_MK,
    SUM(IIF(x.C_MI > 0, POWER(x.C_MI, p.A), 0e0)) / MAX(p.M) AS T_MI,
    SUM(IIF(x.C_MC > 0, POWER(x.C_MC, p.A), 0e0)) / MAX(p.M) AS T_MC
  FROM X3_KEY x CROSS JOIN par p
),
k AS (
  SELECT x.U,
    CAST(x.C_CI AS DOUBLE PRECISION) * x.C_MK * x.C_MI * x.C_MC AS X,
    MINVALUE(1e0,
      POWER(x.C_CI, p.A) / t.T_CI, POWER(x.C_MK, p.A) / t.T_MK,
      POWER(x.C_MI, p.A) / t.T_MI, POWER(x.C_MC, p.A) / t.T_MC) AS PI
  FROM X3_KEY x CROSS JOIN tot t CROSS JOIN par p
  WHERE x.C_CI > 0 AND x.C_MK > 0 AND x.C_MI > 0 AND x.C_MC > 0
),
e AS (
  SELECT s.N, SUM(k.X / k.PI) AS EST, COUNT(*) AS MATCHED
  FROM k CROSS JOIN s
  WHERE (k.U + s.N / 64e0) - FLOOR(k.U + s.N / 64e0) < k.PI
  GROUP BY s.N
),
j AS (SELECT SUM(X) AS J FROM k)
SELECT '1.5/4096' AS E3_A_M,
  COUNT(*) AS SAMPLES,
  AVG(e.EST / j.J) AS R_AVG,
  MIN(e.EST / j.J) AS R_MIN,
  MAX(e.EST / j.J) AS R_MAX,
  SUM(IIF(e.EST BETWEEN j.J / 2 AND j.J * 2, 1, 0)) AS IN_X2,
  SUM(IIF(e.EST BETWEEN j.J / 10 AND j.J * 10, 1, 0)) AS IN_X10,
  SUM(IIF(e.EST > j.J * 2, 1, 0)) AS OVER_X2,
  SUM(IIF(e.EST < j.J / 2, 1, 0)) AS UNDER_X2,
  MIN(e.MATCHED) AS MATCHED_MIN,
  MAX(e.MATCHED) AS MATCHED_MAX
FROM e CROSS JOIN j;
