-- 48_like_estimates.sql - LIKE estimates: Y6 (ab3864fa8a) tail '%%' / '_%' / '%word%'; Y10 (69e659fcfb) NOT LIKE cap; Y11 (69e659fcfb) CHAR with trailing blanks; Y13 (348df09691) '_' fraction grows with fixed chars; W16 'P1___'. Alias tst10like.
-- Each query: tag with the real count, then the estimate (rows=) from set explain under set planonly.
-- Data (deterministic): t1 100 000 rows, z 1 000 000 rows (10 rows per key z.k), t2 1 000 000 rows (99% v = 'ACTIVATION'), d4 100 000 unique 13-char values.
-- Real counts by arithmetic: Name%Surname% 80000; ab_% 99000; P1% 33333; P1___ 33333; c = 'abc' 50000; not like ACTIVATION 10000; ___0000000001 1.
set bail off;
create database 'tst10like' user SYSDBA default character set utf8;
create table t1 (id int not null, nm varchar(40), s varchar(20), code varchar(10), c char(10));
create table z (id int not null, k int, pad varchar(60));
create table t2 (id int not null, v varchar(20));
create table d4 (id int not null, u13 varchar(20));
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 100000) do begin
    insert into t1 values (:i,
      iif(mod(:i, 5) < 4, 'Name' || mod(:i, 1000) || 'Surname' || :i, 'Other' || :i),
      iif(mod(:i, 100) < 99, 'ab' || :i, 'zz' || :i),
      'P' || mod(:i, 3) || lpad(mod(:i, 1000), 3, '0'),
      iif(mod(:i, 2) = 0, 'abc', 'x' || :i));
    insert into d4 values (:i, substring('ABCDEFGHIJKLMNOPQRSTUVWXYZ' from mod(:i, 26) + 1 for 1)
      || substring('ABCDEFGHIJKLMNOPQRSTUVWXYZ' from mod(:i / 26, 26) + 1 for 1)
      || substring('ABCDEFGHIJKLMNOPQRSTUVWXYZ' from mod(:i / 676, 26) + 1 for 1) || lpad(:i, 10, '0'));
    i = i + 1; end
  i = 0;
  while (i < 1000000) do begin
    insert into z values (:i, mod(:i * 7919, 100000), 'zpad' || :i);
    insert into t2 values (:i, iif(mod(:i, 100) < 99, 'ACTIVATION', 'V' || mod(:i, 50000)));
    i = i + 1; end
end^
set term ;^
commit;
create index t1_nm on t1 (nm);
create index t1_s on t1 (s);
create index t1_code on t1 (code);
create index z_k on z (k);
commit;
alter database add extended statistics; commit;
alter database refresh statistics; commit;
connect 'tst10like' user SYSDBA;

select 'Y6a t1: nm like ''Name%Surname%'' (expected 80000)' as tag, count(*) as real_cnt from t1 where nm like 'Name%Surname%';
set planonly on; set explain on;
select count(*) from t1 where nm like 'Name%Surname%';
set explain off; set planonly off; set plan off;
select 'Y6b t1: s like ''ab_%'' (expected 99000)' as tag, count(*) as real_cnt from t1 where s like 'ab_%';
set planonly on; set explain on;
select count(*) from t1 where s like 'ab_%';
set explain off; set planonly off; set plan off;
select 'Y6c t1: code like ''P1%%'' (expected 33333)' as tag, count(*) as real_cnt from t1 where code like 'P1%%';
set planonly on; set explain on;
select count(*) from t1 where code like 'P1%%';
set explain off; set planonly off; set plan off;
select 'Y6d t1: code like ''P1%'' (expected 33333 (control))' as tag, count(*) as real_cnt from t1 where code like 'P1%';
set planonly on; set explain on;
select count(*) from t1 where code like 'P1%';
set explain off; set planonly off; set plan off;
select 'W16 t1: code like ''P1___'' (expected 33333)' as tag, count(*) as real_cnt from t1 where code like 'P1___';
set planonly on; set explain on;
select count(*) from t1 where code like 'P1___';
set explain off; set planonly off; set plan off;
select 'Y10 t2: not (v like ''ACTIVATION'') (expected 10000)' as tag, count(*) as real_cnt from t2 where not (v like 'ACTIVATION');
set planonly on; set explain on;
select count(*) from t2 where not (v like 'ACTIVATION');
set explain off; set planonly off; set plan off;
select 'Y10c t2: v <> ''ACTIVATION'' (expected 10000 (control))' as tag, count(*) as real_cnt from t2 where v <> 'ACTIVATION';
set planonly on; set explain on;
select count(*) from t2 where v <> 'ACTIVATION';
set explain off; set planonly off; set plan off;
select 'Y11 t1: c like ''abc       '' (expected 50000)' as tag, count(*) as real_cnt from t1 where c like 'abc       ';
set planonly on; set explain on;
select count(*) from t1 where c like 'abc       ';
set explain off; set planonly off; set plan off;
select 'Y11c t1: c = ''abc'' (expected 50000 (control))' as tag, count(*) as real_cnt from t1 where c = 'abc';
set planonly on; set explain on;
select count(*) from t1 where c = 'abc';
set explain off; set planonly off; set plan off;
select 'Y13 d4: u13 like ''___0000000001'' (expected 1)' as tag, count(*) as real_cnt from d4 where u13 like '___0000000001';
set planonly on; set explain on;
select count(*) from d4 where u13 like '___0000000001';
set explain off; set planonly off; set plan off;
select 'Y13c d4: u13 like ''A____________'' (expected 3847 (control))' as tag, count(*) as real_cnt from d4 where u13 like 'A____________';
set planonly on; set explain on;
select count(*) from d4 where u13 like 'A____________';
set explain off; set planonly off; set plan off;

-- ===== Y6 plan impact: the same rows, 'ab_%' -> NL by Z_K (bad), 'ab%' -> HJ (good). Expected 990000 rows. =====
set explain on;
set stats on;
select 'J1 t1 join z, t1.s like ''ab_%''' as tag, count(*) as cnt, max(z.pad) as mx from t1 join z on z.k = t1.id where t1.s like 'ab_%';
select 'J2 t1 join z, t1.s like ''ab%''' as tag, count(*) as cnt, max(z.pad) as mx from t1 join z on z.k = t1.id where t1.s like 'ab%';
