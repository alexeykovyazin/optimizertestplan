-- Test 87: review of the optimizer notes 4.60 - 4.63 (constants at prepare, invariant calls, OR -> IN).
-- Every case returned other rows, raised a new error or lost a plan on the build 82f271652d and returns the result of
-- the build before these changes (aa214e362c) after the review fixes.
-- Expected results (the same on the build before the changes and on the build with the fixes):
--   PA: 3 X3, 2 X2, 1 X1              (82f271652d: 3 X3 three times - the assigned input parameter was an invariant)
--   PB: 3                             (82f271652d: 50 - WHILE (ABS(n) > 0) never saw n change)
--   PC: q1, q2, q3                    (82f271652d: q1 three times)
--   PD: 1 2 2 3 3 4                   (82f271652d: 1 2 3 - the IN list of the parameters was computed once)
--   PE: V1, V10, V11                  (target of EXECUTE STATEMENT ... INTO)
--   PF: w1, w20, w21                  (target of RETURNING_VALUES and of an assignment)
--   PG: s1, s101, s201                (the parameter is assigned by a sub-routine)
--   FH: 36,24,12,                     (a function, a DETERMINISTIC function of the parameter)
--   PI: CONST11, CONST22, CONST33     (control: a parameter that is only read stays invariant per call)
--   V1: 2843   (82f271652d: 0)        case-insensitive column, the values 'a' and 'B'
--   V2: 2843   (82f271652d: 0)        the same with the field on the right
--   V3: 1398   (82f271652d: 682)      one value with a COLLATE of its own
--   V4: 291    (82f271652d: error)    a TIMESTAMP field, a TIMESTAMP and a DATE value
--   V5: 2      (82f271652d: 1)        a text field, a number and a string
--   V6: 1      (82f271652d: error)    a text field, a number and a string that is not a number (row '1' only)
--   V7: 2843   (82f271652d: 0)        the same as V1 with an index on the column (List Scan)
--   D1: 1, D2: 3, D3: 2               (82f271652d: 0, error, 1) a string against DECFLOAT(34)
--   W1: 0      (82f271652d: 1)        BETWEEN with a string literal as the tested value
-- Expected plans: X1 and X2 "PLAN (T INDEX (IP))" (82f271652d: T_I, and X2 fails "index IP cannot be used");
--   X3 (the IN list written in the query) takes IP too with the fixes - it took T_I before.
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create sequence g;
create table t (
  id int not null primary key,
  i int,
  j int,
  s varchar(20),
  ci varchar(10) collate unicode_ci,
  ts timestamp);
create table u (id int not null primary key, i int, k int);
create table td (id int, df decfloat(34), vc varchar(10));
commit;
set term ^;
execute block as
  declare k int = 1;
  declare h int;
begin
  while (k <= 3000) do
  begin
    h = mod(k * 7919 + 13, 100003);
    insert into t (id, i, j, s, ci, ts) values (:k,
      iif(mod(:k, 7) = 0, null, mod(:h, 12)),
      iif(mod(:k, 11) = 0, null, mod(:h, 5)),
      iif(mod(:k, 13) = 0, null, iif(mod(:h, 4) = 0, 'a', iif(mod(:h, 4) = 1, 'b ', iif(mod(:h, 4) = 2, 'A', '12')))),
      iif(mod(:k, 19) = 0, null, iif(mod(:h, 3) = 0, 'a', iif(mod(:h, 3) = 1, 'A', 'b'))),
      iif(mod(:k, 31) = 0, null, dateadd(mod(:h, 10) day to timestamp '2020-01-01 12:00:00')));
    k = k + 1;
  end
  k = 1;
  while (k <= 60) do
  begin
    insert into u (id, i, k) values (:k, iif(mod(:k, 6) = 0, null, mod(:k, 12)), mod(:k, 4));
    k = k + 1;
  end
end^
create function fdet (a int) returns int deterministic as begin return a * 2; end^
create procedure pa (n int) returns (r int, s varchar(10)) as
begin
  while (n > 0) do begin r = abs(n); s = upper('x' || n); suspend; n = n - 1; end
end^
create procedure pb (n int) returns (r int) as
begin
  r = 0;
  while (abs(n) > 0 and r < 50) do begin n = n - 1; r = r + 1; end
  suspend;
end^
create procedure pc (n int) returns (k int, s varchar(10)) as
begin
  for select id, lower('Q' || :n) from u where id <= 3 order by id into :k, :s do
  begin
    suspend;
    n = n + 1;
  end
end^
create procedure pd (x int, y int) returns (r int) as
begin
  while (x <= 3) do
  begin
    for select id from u where id = :x or id = :y order by id into :r do suspend;
    x = x + 1; y = y + 1;
  end
end^
create procedure pe (n int) returns (k int, s varchar(20)) as
begin
  k = 0;
  while (k < 3) do
  begin
    s = upper('v' || n);
    suspend;
    execute statement 'select ' || (k + 10) || ' from rdb$database' into :n;
    k = k + 1;
  end
end^
create procedure pf_out returns (o int) as begin o = gen_id(g, 1); end^
create procedure pf (n int) returns (k int, s varchar(20)) as
begin
  k = 0;
  while (k < 3) do
  begin
    s = replace('v' || n, 'v', 'w');
    suspend;
    execute procedure pf_out returning_values :n;
    n = n * 0 + k + 20;
    k = k + 1;
  end
end^
create procedure pg (n int) returns (k int, s varchar(20)) as
  declare procedure sub as begin n = n + 100; end
begin
  k = 0;
  while (k < 3) do
  begin
    s = lower('S' || n);
    suspend;
    execute procedure sub;
    k = k + 1;
  end
end^
create function fh (n int) returns varchar(60) as
  declare s varchar(60) = '';
begin
  while (n > 0) do begin s = s || abs(n) || fdet(n) || ','; n = n - 1; end
  return s;
end^
create procedure pi (n int) returns (s varchar(20)) as
begin
  s = upper('const' || n) || abs(n);
  suspend;
end^
set term ;^
commit;
insert into td values (1, 0.1, '10');
insert into td values (2, 1, '9');
insert into td values (3, 100, '1');
commit;
create index t_i on t (i);
create index t_s on t (s);
commit;

-- P: an input parameter the routine assigns
select 'PA' q, r, s from pa(3);
select 'PB' q, r from pb(3);
select 'PC' q, k, s from pc(1);
select 'PD' q, r from pd(1, 2);
select 'PE' q, k, s from pe(1);
select 'PF' q, k, s from pf(1);
select 'PG' q, k, s from pg(1);
select 'FH' q, fh(3) from rdb$database;
select 'PI' q, u.id, p.s from u cross join pi(u.id) p where u.id <= 3 order by u.id;

-- V: an OR of equalities whose IN list has other comparison rules
select 'V1' q, count(*) from t where ci = 'a' or ci = 'B';
select 'V2' q, count(*) from t where 'a' = ci or 'B' = ci;
select 'V3' q, count(*) from t where s = 'a' or s = cast('A' as varchar(5) character set utf8) collate unicode_ci;
select 'V4' q, count(*) from t where ts = timestamp '2020-01-01 12:00:00' or ts = date '2020-01-03';
select 'V5' q, count(*) from td where vc = 10 or vc = '9';
select 'V6' q, count(*) from td where id = 3 and (vc = 1 or vc = 'abc');
create index t_ci on t (ci);
commit;
select 'V7' q, count(*) from t where ci = 'a' or ci = 'B';
drop index t_ci;
commit;

-- D, W: string literals at prepare
select 'D1' q, count(*) from td where df = '1E-1';
select 'D2' q, count(*) from td where df > '-Infinity';
select 'D3' q, count(*) from td where df between '1E-1' and '1E0';
select 'W1' q, count(*) from rdb$database where '15.06.2024' between date '2024-01-01' and '01.01.2025';

-- X: a conditional index whose condition is the OR of the query
create index ip on t (j) where i = 1 or i = 2;
commit;
set plan on;
select 'X1' q, count(*) from t where (i = 1 or i = 2) and j = 3;
select 'X2' q, count(*) from t where (i = 1 or i = 2) and j = 3 plan (t index (ip));
select 'X3' q, count(*) from t where i in (1, 2) and j = 3;
set plan off;
