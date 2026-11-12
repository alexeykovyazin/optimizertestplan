-- 40_pairfiltered.sql - W7 (90da978a89): pairFiltered position has no floor; NL with 2.5M fetches instead of HJ. Alias tst9pf.
-- vE pf: finding 5 (pairFiltered without a floor). Correlated residual filters f1 = f2 on the join-driven position b.
create database 'tst9pf' user SYSDBA page_size 8192;
alter database add extended statistics; commit;
create table a (id int not null primary key, v int);
create table b (id int not null primary key, a_id int, f1 int, f2 int, e_k int);
create table e (id int not null primary key, k int, flag int);
commit;
set term ^;
execute block as declare i int = 1; begin
  while (i <= 1000) do begin insert into a values(:i, :i); i = i + 1; end
  i = 1;
  while (i <= 100000) do begin
    insert into b values(:i, mod(:i, 1000) + 1, mod(trunc(:i / 1000), 100), mod(trunc(:i / 1000), 100), mod(:i, 2));
    insert into e values(:i, mod(:i, 2), iif(mod(:i, 1000) = 0, 1, 0));
    i = i + 1;
  end
end^
set term ;^
commit;
create index b_a on b(a_id);
create index e_k on e(k);
commit;
alter database refresh statistics; commit;
connect 'tst9pf' user SYSDBA;
set explain on; set stats on;
-- Q1 one a row: real 1
select 'Q1' q, count(*) from a join b on b.a_id = a.id where a.id = 5 and b.f1 = 1 and b.f2 = 1;
-- Q2 49 a rows, deeper e by a non-selective index with a rare filter: real 2500
select 'Q2' q, count(*) from a join b on b.a_id = a.id join e on e.k = b.e_k where a.v < 50 and b.f1 = 1 and b.f2 = 1 and e.flag = 1;
select 'Q2' q, count(*) from a join b on b.a_id = a.id join e on e.k = b.e_k where a.v < 50 and b.f1 = 1 and b.f2 = 1 and e.flag = 1;
select 'Q2h' q, count(*) from a join b on b.a_id = a.id join e on e.k = b.e_k where a.v < 50 and b.f1 = 1 and b.f2 = 1 and e.flag = 1
  plan hash (join (a natural, b index (b_a)), e natural);
select 'Q2n' q, count(*) from a join b on b.a_id = a.id join e on e.k = b.e_k where a.v < 50 and b.f1 = 1 and b.f2 = 1 and e.flag = 1
  plan join (a natural, b index (b_a), e index (e_k));
-- Q3 same with a single residual filter (b.f1 = 1 only): real 2500
select 'Q3' q, count(*) from a join b on b.a_id = a.id join e on e.k = b.e_k where a.v < 50 and b.f1 = 1 and e.flag = 1;
-- Q4 few a rows (5): real 300 (3 odd a ids x 100)
select 'Q4' q, count(*) from a join b on b.a_id = a.id join e on e.k = b.e_k where a.v < 6 and b.f1 = 1 and b.f2 = 1 and e.flag = 1;
