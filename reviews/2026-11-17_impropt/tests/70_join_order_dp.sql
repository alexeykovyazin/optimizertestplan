-- 70_join_order_dp.sql - the join order search by dynamic programming (JoinOrderDP, commit e1a02d6eb6).
-- Three aliases with the same data:
--   tst20dpoff - JoinOrderDP is off (the default);
--   tst20dp12  - JoinOrderDP = true, JoinOrderDPBudget = 12 (the budget ends at the first levels);
--   tst20dp100 - JoinOrderDP = true, JoinOrderDPBudget = 100 (the budget ends in the middle of the search).
-- D1: 10 tables around t (a star with the dimension tables). D2, D3: two groups of tables without a join
-- condition between the groups (the join order is found in two rounds).
-- Expected: the counts are equal in the three aliases - D1 8580, D2 200000, D3 1200000; no table appears
-- twice in a plan.
-- On the commit e1a02d6eb6: tst20dp12 D1 - KT and T are in the plan twice; tst20dp100 D1 - IT, KT, MI, T are
-- in the plan twice and the count is 25740; D2 in both DP aliases - "request size limit exceeded".
set bail off;
create database 'tst20dpoff' user SYSDBA;
create table kt (id int primary key, kind varchar(10));
create table it (id int primary key, info varchar(10));
create table cn (id int primary key, country varchar(10));
create table n (id int primary key, gender char(1));
create table t (id int primary key, kind_id int, yr int);
create table mi (id int primary key, movie_id int, info_type_id int);
create table mc (id int primary key, movie_id int, company_id int);
create table ci (id int primary key, movie_id int, person_id int);
create table mk (id int primary key, movie_id int, keyword_id int);
create table k (id int primary key, kw varchar(10));
create table p (id int primary key, v int);
create table q (id int primary key, p_id int, v int);
commit;
set term ^;
execute block as
declare i int = 0;
begin
  while (i < 7) do begin insert into kt values (:i, 'k' || :i); i = i + 1; end
  i = 0;
  while (i < 100) do begin insert into it values (:i, 'i' || mod(:i, 20)); i = i + 1; end
  i = 0;
  while (i < 5000) do begin insert into cn values (:i, 'c' || mod(:i, 50)); i = i + 1; end
  i = 0;
  while (i < 20000) do begin insert into n values (:i, iif(mod(:i, 3) = 0, 'f', 'm')); i = i + 1; end
  i = 0;
  while (i < 2000) do begin insert into k values (:i, 'w' || mod(:i, 100)); i = i + 1; end
  i = 0;
  while (i < 20000) do begin insert into t values (:i, mod(:i, 7), 1950 + mod(:i * 7, 70)); i = i + 1; end
  i = 0;
  while (i < 60000) do begin insert into mi values (:i, mod(:i * 13, 20000), mod(:i, 100)); i = i + 1; end
  i = 0;
  while (i < 40000) do begin insert into mc values (:i, mod(:i * 17, 15000), mod(:i * 3, 5000)); i = i + 1; end
  i = 0;
  while (i < 80000) do begin insert into ci values (:i, mod(:i * 19, 18000), mod(:i * 11, 20000)); i = i + 1; end
  i = 0;
  while (i < 50000) do begin insert into mk values (:i, mod(:i * 23, 12000), mod(:i * 5, 2000)); i = i + 1; end
  i = 0;
  while (i < 50) do begin insert into p values (:i, mod(:i, 5)); i = i + 1; end
  i = 0;
  while (i < 400) do begin insert into q values (:i, mod(:i, 50), mod(:i, 7)); i = i + 1; end
end^
set term ;^
commit;
create index mi_movie on mi (movie_id);
create index mi_it on mi (info_type_id);
create index mc_movie on mc (movie_id);
create index mc_cn on mc (company_id);
create index ci_movie on ci (movie_id);
create index ci_n on ci (person_id);
create index mk_movie on mk (movie_id);
create index mk_k on mk (keyword_id);
create index t_kind on t (kind_id);
create index q_p on q (p_id);
commit;
select 'tst20dpoff' as alias from rdb$database;
set plan on;
select 'D1' as q, count(*) from t, kt, mi, it, mc, cn, ci, n, mk, k
where t.kind_id = kt.id and mi.movie_id = t.id and mi.info_type_id = it.id
  and mc.movie_id = t.id and mc.company_id = cn.id and ci.movie_id = t.id and ci.person_id = n.id
  and mk.movie_id = t.id and mk.keyword_id = k.id
  and mi.movie_id = mc.movie_id and mc.movie_id = ci.movie_id and ci.movie_id = mk.movie_id
  and kt.kind in ('k1', 'k2') and it.info in ('i3', 'i5', 'i7') and cn.country <> 'c7' and n.gender = 'f' and k.kw <> 'w5'
  and t.yr > 1990;
select 'D2' as q, count(*) from p, q, mk, k
where q.p_id = p.id and mk.keyword_id = k.id and k.kw = 'w5' and p.v = 1;
select 'D3' as q, count(*) from p, q, t, mi, it
where q.p_id = p.id and mi.movie_id = t.id and mi.info_type_id = it.id and it.info = 'i3' and t.yr > 2010;
set plan off;
commit;
create database 'tst20dp12' user SYSDBA;
create table kt (id int primary key, kind varchar(10));
create table it (id int primary key, info varchar(10));
create table cn (id int primary key, country varchar(10));
create table n (id int primary key, gender char(1));
create table t (id int primary key, kind_id int, yr int);
create table mi (id int primary key, movie_id int, info_type_id int);
create table mc (id int primary key, movie_id int, company_id int);
create table ci (id int primary key, movie_id int, person_id int);
create table mk (id int primary key, movie_id int, keyword_id int);
create table k (id int primary key, kw varchar(10));
create table p (id int primary key, v int);
create table q (id int primary key, p_id int, v int);
commit;
set term ^;
execute block as
declare i int = 0;
begin
  while (i < 7) do begin insert into kt values (:i, 'k' || :i); i = i + 1; end
  i = 0;
  while (i < 100) do begin insert into it values (:i, 'i' || mod(:i, 20)); i = i + 1; end
  i = 0;
  while (i < 5000) do begin insert into cn values (:i, 'c' || mod(:i, 50)); i = i + 1; end
  i = 0;
  while (i < 20000) do begin insert into n values (:i, iif(mod(:i, 3) = 0, 'f', 'm')); i = i + 1; end
  i = 0;
  while (i < 2000) do begin insert into k values (:i, 'w' || mod(:i, 100)); i = i + 1; end
  i = 0;
  while (i < 20000) do begin insert into t values (:i, mod(:i, 7), 1950 + mod(:i * 7, 70)); i = i + 1; end
  i = 0;
  while (i < 60000) do begin insert into mi values (:i, mod(:i * 13, 20000), mod(:i, 100)); i = i + 1; end
  i = 0;
  while (i < 40000) do begin insert into mc values (:i, mod(:i * 17, 15000), mod(:i * 3, 5000)); i = i + 1; end
  i = 0;
  while (i < 80000) do begin insert into ci values (:i, mod(:i * 19, 18000), mod(:i * 11, 20000)); i = i + 1; end
  i = 0;
  while (i < 50000) do begin insert into mk values (:i, mod(:i * 23, 12000), mod(:i * 5, 2000)); i = i + 1; end
  i = 0;
  while (i < 50) do begin insert into p values (:i, mod(:i, 5)); i = i + 1; end
  i = 0;
  while (i < 400) do begin insert into q values (:i, mod(:i, 50), mod(:i, 7)); i = i + 1; end
end^
set term ;^
commit;
create index mi_movie on mi (movie_id);
create index mi_it on mi (info_type_id);
create index mc_movie on mc (movie_id);
create index mc_cn on mc (company_id);
create index ci_movie on ci (movie_id);
create index ci_n on ci (person_id);
create index mk_movie on mk (movie_id);
create index mk_k on mk (keyword_id);
create index t_kind on t (kind_id);
create index q_p on q (p_id);
commit;
select 'tst20dp12' as alias from rdb$database;
set plan on;
select 'D1' as q, count(*) from t, kt, mi, it, mc, cn, ci, n, mk, k
where t.kind_id = kt.id and mi.movie_id = t.id and mi.info_type_id = it.id
  and mc.movie_id = t.id and mc.company_id = cn.id and ci.movie_id = t.id and ci.person_id = n.id
  and mk.movie_id = t.id and mk.keyword_id = k.id
  and mi.movie_id = mc.movie_id and mc.movie_id = ci.movie_id and ci.movie_id = mk.movie_id
  and kt.kind in ('k1', 'k2') and it.info in ('i3', 'i5', 'i7') and cn.country <> 'c7' and n.gender = 'f' and k.kw <> 'w5'
  and t.yr > 1990;
select 'D2' as q, count(*) from p, q, mk, k
where q.p_id = p.id and mk.keyword_id = k.id and k.kw = 'w5' and p.v = 1;
select 'D3' as q, count(*) from p, q, t, mi, it
where q.p_id = p.id and mi.movie_id = t.id and mi.info_type_id = it.id and it.info = 'i3' and t.yr > 2010;
set plan off;
commit;
create database 'tst20dp100' user SYSDBA;
create table kt (id int primary key, kind varchar(10));
create table it (id int primary key, info varchar(10));
create table cn (id int primary key, country varchar(10));
create table n (id int primary key, gender char(1));
create table t (id int primary key, kind_id int, yr int);
create table mi (id int primary key, movie_id int, info_type_id int);
create table mc (id int primary key, movie_id int, company_id int);
create table ci (id int primary key, movie_id int, person_id int);
create table mk (id int primary key, movie_id int, keyword_id int);
create table k (id int primary key, kw varchar(10));
create table p (id int primary key, v int);
create table q (id int primary key, p_id int, v int);
commit;
set term ^;
execute block as
declare i int = 0;
begin
  while (i < 7) do begin insert into kt values (:i, 'k' || :i); i = i + 1; end
  i = 0;
  while (i < 100) do begin insert into it values (:i, 'i' || mod(:i, 20)); i = i + 1; end
  i = 0;
  while (i < 5000) do begin insert into cn values (:i, 'c' || mod(:i, 50)); i = i + 1; end
  i = 0;
  while (i < 20000) do begin insert into n values (:i, iif(mod(:i, 3) = 0, 'f', 'm')); i = i + 1; end
  i = 0;
  while (i < 2000) do begin insert into k values (:i, 'w' || mod(:i, 100)); i = i + 1; end
  i = 0;
  while (i < 20000) do begin insert into t values (:i, mod(:i, 7), 1950 + mod(:i * 7, 70)); i = i + 1; end
  i = 0;
  while (i < 60000) do begin insert into mi values (:i, mod(:i * 13, 20000), mod(:i, 100)); i = i + 1; end
  i = 0;
  while (i < 40000) do begin insert into mc values (:i, mod(:i * 17, 15000), mod(:i * 3, 5000)); i = i + 1; end
  i = 0;
  while (i < 80000) do begin insert into ci values (:i, mod(:i * 19, 18000), mod(:i * 11, 20000)); i = i + 1; end
  i = 0;
  while (i < 50000) do begin insert into mk values (:i, mod(:i * 23, 12000), mod(:i * 5, 2000)); i = i + 1; end
  i = 0;
  while (i < 50) do begin insert into p values (:i, mod(:i, 5)); i = i + 1; end
  i = 0;
  while (i < 400) do begin insert into q values (:i, mod(:i, 50), mod(:i, 7)); i = i + 1; end
end^
set term ;^
commit;
create index mi_movie on mi (movie_id);
create index mi_it on mi (info_type_id);
create index mc_movie on mc (movie_id);
create index mc_cn on mc (company_id);
create index ci_movie on ci (movie_id);
create index ci_n on ci (person_id);
create index mk_movie on mk (movie_id);
create index mk_k on mk (keyword_id);
create index t_kind on t (kind_id);
create index q_p on q (p_id);
commit;
select 'tst20dp100' as alias from rdb$database;
set plan on;
select 'D1' as q, count(*) from t, kt, mi, it, mc, cn, ci, n, mk, k
where t.kind_id = kt.id and mi.movie_id = t.id and mi.info_type_id = it.id
  and mc.movie_id = t.id and mc.company_id = cn.id and ci.movie_id = t.id and ci.person_id = n.id
  and mk.movie_id = t.id and mk.keyword_id = k.id
  and mi.movie_id = mc.movie_id and mc.movie_id = ci.movie_id and ci.movie_id = mk.movie_id
  and kt.kind in ('k1', 'k2') and it.info in ('i3', 'i5', 'i7') and cn.country <> 'c7' and n.gender = 'f' and k.kw <> 'w5'
  and t.yr > 1990;
select 'D2' as q, count(*) from p, q, mk, k
where q.p_id = p.id and mk.keyword_id = k.id and k.kw = 'w5' and p.v = 1;
select 'D3' as q, count(*) from p, q, t, mi, it
where q.p_id = p.id and mi.movie_id = t.id and mi.info_type_id = it.id and it.info = 'i3' and t.yr > 2010;
set plan off;
commit;
