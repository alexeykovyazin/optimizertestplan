-- Test 88: review of the compile time folding of constants (the optimizer note 4.64).
-- Every case answered in another way on the build b1494783a9 (the folding) than on the build before it
-- (3ede1e6046). With the review fixes the answers are those of the build before the folding.
-- Expected results:
--   S1: [ab]       (b1494783a9: [ab      ])  LIST(DISTINCT) over a folded string
--   S2: [ab]       (b1494783a9: [ab      ])  the same over a column of a view
--   S3: one row with an empty string  (b1494783a9: conversion error from string "1")  DISTINCT, a string of no length
--   S4: 1          (b1494783a9: 5)           COUNT(DISTINCT), a string of no length
--   S5: [|]        (b1494783a9: [,,,,|])     LIST(DISTINCT), a string of no length
--   FS (one statement text, run three times: the second and the third run take the statement of the cache):
--       ...117E+38; ...116E+38 after SET DECFLOAT ROUND FLOOR; the error "Decimal float inexact result" after
--       SET DECFLOAT TRAPS TO INEXACT  (b1494783a9: ...117E+38 three times)
--   F4: ...117E+38, F5: ...116E+38, F6: the error  (b1494783a9: ...117E+38 three times)
--       a procedure compiled before the settings of the session change
--   N1: differs    (b1494783a9: same)        TIMESTAMP - 'NOW' in a procedure of the dialect 1, called twice
--   T1, T2, T3: every explained plan holds "Top N Sort" (b1494783a9: a full "Sort" in every plan).
--       "First N Records" has rows=10.00 in T1, rows=5.00 in T2 and T3 (before the folding: rows=1000.00)
--   C1: 3, 2020-01-02, AB, 5 - the control: the values of the folded expressions
-- The connection character set is UTF8: a literal of one byte per character is not padded.
set bail off;
set names utf8;
create database 'tst2def' user SYSDBA default character set utf8;
create table t (
  id int not null primary key,
  i int,
  c char(5),
  ts timestamp);
commit;
set term ^;
execute block as
  declare k int = 1;
  declare h int;
begin
  while (k <= 3000) do
  begin
    h = mod(k * 7919 + 13, 100003);
    insert into t (id, i, c, ts) values (:k, mod(:h, 12), iif(mod(:h, 3) = 0, 'x', 'yz'),
      dateadd(mod(:h, 10) day to timestamp '2020-01-01 12:00:00'));
    k = k + 1;
  end
end^
create procedure pf returns (a decfloat(34)) as
begin
  a = 1234567890123456789012345678901234567890 / 3;
  suspend;
end^
set term ;^
create view v as select id, left('abcd', 2) w from t;
commit;

-- S: the descriptor of a folded string
select 'S1' q, '[' || list(distinct left('abcd', 2)) || ']' from t where id <= 3;
select 'S2' q, '[' || list(distinct w) || ']' from v where id <= 3;
select distinct 'S3' q, left('abc', 0) v from t where id <= 3;
select 'S4' q, count(distinct left('abc', 0)) from t where id <= 5;
select 'S5' q, '[' || list(distinct left('abc', 0)) || '|]' from t where id <= 5;

-- F: DECFLOAT follows the settings of the session
select 'FS' q, 1234567890123456789012345678901234567890 / 3 a from rdb$database;
select 'F4' q, a from pf;
set decfloat round floor;
select 'FS' q, 1234567890123456789012345678901234567890 / 3 a from rdb$database;
select 'F5' q, a from pf;
set decfloat traps to inexact;
select 'FS' q, 1234567890123456789012345678901234567890 / 3 a from rdb$database;
select 'F6' q, a from pf;
set decfloat traps to;
set decfloat round half_up;

-- N: a string in the arithmetic of dates is read by the clock (the dialect 1)
set sql dialect 1;
set term ^;
create procedure pn returns (r double precision) as
begin
  r = cast('2030-01-01 00:00:00' as timestamp) - 'NOW';
  suspend;
end^
set term ;^
commit;
set sql dialect 3;
set heading off;
select rdb$set_context('USER_SESSION', 'N1', cast(r * 86400000 as bigint)) from pn;
select count(*) from t a cross join t b where a.i + b.i = 1;
select 'N1' q, iif(cast(rdb$get_context('USER_SESSION', 'N1') as bigint) = cast(r * 86400000 as bigint), 'same', 'differs')
  from pn;
set heading on;

-- T: the limit of the rows is an expression of constants
set explain on;
set planonly on;
select 'T1' q, id from t order by c, ts rows 1 to 10;
select first (2 + 3) 'T2' q, id from t order by c, ts;
select 'T3' q, id from (select id, i from t order by c, ts rows 2 to 6) where i > 0;
set planonly off;
set explain off;

-- C: the control
select 'C1' q, 1 + 2 a, dateadd(1 day to date '2020-01-01') b, upper('ab') c, abs(-5) d from rdb$database;
