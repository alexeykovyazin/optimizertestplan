-- 50_full_join_subq.sql - FULL JOIN with a correlated sub-query in ON: the reversed half runs the sub-query
-- as "Table P Full Scan" for every row pair, 50-200 times slower than HQbird 5.0. Alias tst10oj.
-- Cause: OuterJoin::generate() (src/jrd/optimizer/OuterJoin.cpp:123-138, commit ec3910caed) deactivates both
-- streams first and clones the ON conjuncts after it; the clone compiles the sub-query again, and with
-- the parent streams inactive the correlation p.id = a.x cannot use the P primary key. HQbird 5.0 clones
-- before the deactivation. It is not specific to the hash join: the NL form (Q6) is slow too.
-- LEFT / RIGHT JOIN have no reversed half and are fast.
-- Data: b 8 000 rows, a 20 000 rows (bid -> b.id, 10% NULL; x = mod(i, 3000)), p 4 000 rows (PK id).
-- Expected values (HQbird 5.0, equal to the R* reference rows): see the "expected" text in every row.
-- Look at Fetches: good ~0.3 M, bad 30-74 M. Time on b69da49179: 3-10 s per slow query, ~50 s in all.
-- On 06041718cc Q1, Q3-Q5, C2, C3 and R1 are fast but wrong (review W1: the ON conjunct was lost); Q2, Q6 are slow there too.
set bail off;
create database 'tst10oj' user SYSDBA page_size 8192;
create table b (id int not null primary key, v varchar(10));
create table a (id int not null primary key, bid int references b(id), x int);
create table p (id int not null primary key, name varchar(10));
commit;
set term ^;
execute block as declare i int = 1; begin
  while (i <= 8000) do begin insert into b values (:i, 'v' || mod(:i, 7)); i = i + 1; end
  i = 1;
  while (i <= 20000) do begin
    insert into a values (:i, iif(mod(:i, 10) = 0, null, mod(:i * 3, 8000) + 1), mod(:i, 3000));
    i = i + 1; end
  i = 1;
  while (i <= 4000) do begin insert into p values (:i, iif(mod(:i, 3) = 0, 'v' || mod(:i, 7), 'q' || :i)); i = i + 1; end
end^
set term ;^
commit;
alter database add extended statistics; commit;
alter database refresh statistics; commit;
connect 'tst10oj' user SYSDBA;

set list on;
-- reference for Q1: (a LEFT JOIN b) UNION ALL (b rows without a match), both parts fast on every build
select 'R1 reference for Q1, Q6' as tag, count(*) as cnt, sum(coalesce(aid, 0) + coalesce(bid, 0)) as sum_id from (
  select a.id aid, b.id bid from a left join b on b.id = a.bid and b.v not in (select p.name from p where p.id = a.x)
  union all
  select null, b.id from b where not exists
    (select 1 from a where a.bid = b.id and b.v not in (select p.name from p where p.id = a.x)));

set stats on;
select 'Q1 full, not in (sub-query on a), expected 20800 / 269510335' as tag, count(*) as cnt, sum(coalesce(a.id, 0) + coalesce(b.id, 0)) as sum_id
  from a full join b on b.id = a.bid and b.v not in (select p.name from p where p.id = a.x);
select 'Q2 full, not in (sub-query on b), expected 22000 / 270423600' as tag, count(*) as cnt, sum(coalesce(a.id, 0) + coalesce(b.id, 0)) as sum_id
  from a full join b on b.id = a.bid and b.v not in (select p.name from p where p.id = b.id);
select 'Q3 full, exists, expected 27143 / 232014000' as tag, count(*) as cnt, sum(coalesce(a.id, 0) + coalesce(b.id, 0)) as sum_id
  from a full join b on b.id = a.bid and exists (select 1 from p where p.id = a.x and p.name = b.v);
select 'Q4 full, in, expected 27143 / 232014000' as tag, count(*) as cnt, sum(coalesce(a.id, 0) + coalesce(b.id, 0)) as sum_id
  from a full join b on b.id = a.bid and b.v in (select p.name from p where p.id = a.x);
select 'Q5 full, scalar sub-query, expected 20800 / 269510335' as tag, count(*) as cnt, sum(coalesce(a.id, 0) + coalesce(b.id, 0)) as sum_id
  from a full join b on b.id = a.bid and b.v <> (select p.name from p where p.id = a.x);
select 'Q6 full, nested loop (no equality), expected 20800 / 269510335' as tag, count(*) as cnt, sum(coalesce(a.id, 0) + coalesce(b.id, 0)) as sum_id
  from a full join b on b.id between a.bid and a.bid and b.v not in (select p.name from p where p.id = a.x);
-- controls: no sub-query; LEFT and RIGHT JOIN with the same sub-query
select 'C1 full, plain <>, expected 21828 / 267003815' as tag, count(*) as cnt, sum(coalesce(a.id, 0) + coalesce(b.id, 0)) as sum_id
  from a full join b on b.id = a.bid and b.v <> 'v1';
select 'C2 left, not in, expected 20000 / 266313535' as tag, count(*) as cnt, sum(coalesce(a.id, 0) + coalesce(b.id, 0)) as sum_id
  from a left join b on b.id = a.bid and b.v not in (select p.name from p where p.id = a.x);
select 'C3 right, not in, expected 17943 / 240939799' as tag, count(*) as cnt, sum(coalesce(a.id, 0) + coalesce(b.id, 0)) as sum_id
  from a right join b on b.id = a.bid and b.v not in (select p.name from p where p.id = a.x);
set stats off;
set list off;

-- plans: on b69da49179 two of the four "Sub-query" blocks of P1 are "Table P Full Scan"
set planonly on;
set explain on;
select count(*) from a full join b on b.id = a.bid and b.v not in (select p.name from p where p.id = a.x);
select count(*) from a full join b on b.id between a.bid and a.bid and b.v not in (select p.name from p where p.id = a.x);
set explain off;
set planonly off;
